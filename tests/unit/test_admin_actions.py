"""Unit tests for the class-based admin Action framework.

These tests exercise the primitives in isolation: result types, prompt validation,
the orchestration in ``Action.run`` (scope, bulk cap, authorization, background,
audit), and the two shipped examples. No HTTP server and no ORM are involved.
"""

from __future__ import annotations

import csv
import io
from types import SimpleNamespace

import pytest

from flaxon.admin.actions import (
    BULK,
    SINGLE,
    STANDALONE,
    Action,
    ActionResult,
    ApproveOrders,
    ExportCsv,
    Prompt,
)
from flaxon.exceptions import BadRequest, Forbidden


class FakeAuth:
    def __init__(self, allowed: set[str] | None = None) -> None:
        self.allowed = allowed or set()

    async def has_permission_async(self, user, permission, resource=None) -> bool:
        return permission in self.allowed


class FakeStore:
    def __init__(self, queued: list[dict] | None = None) -> None:
        self.queued = queued if queued is not None else []
        self.handlers: dict[str, object] = {}

    def enqueue(self, name, payload, **kwargs):
        self.queued.append({"name": name, "payload": payload})
        return SimpleNamespace(id=f"job-{len(self.queued)}")

    def register(self, name, handler):
        self.handlers[name] = handler


class FakeDashboard:
    def __init__(self, allowed: set[str] | None = None, limit: int = 100) -> None:
        self.config = SimpleNamespace(action_bulk_limit=limit)
        self.auth = FakeAuth(allowed)
        self.job_store = FakeStore()
        self.job_worker = FakeStore()
        self.activities: list[dict] = []
        self.url_prefix = "/admin"
        self.action_results: dict[str, ActionResult] = {}

    def record_activity(self, action, resource, request, record_id=None, **details):
        self.activities.append({"action": action, "resource": resource, "record_id": record_id, **details})

    def permission_for_action(self, model_name, action):
        return f"{model_name}.{action}_{model_name}"


async def _run(action, ids, params=None, dashboard=None, scope=BULK):
    dashboard = dashboard or FakeDashboard()
    return await action.run(
        ids,
        params or {},
        dashboard=dashboard,
        request=None,
        user=SimpleNamespace(username="admin"),
        model_name="order",
        admin_model=None,
    )


# --- ActionResult ---------------------------------------------------------


def test_result_factories_set_kind_and_payload():
    ok = ActionResult.ok("Done", data={"count": 2})
    assert ok.kind == "message"
    assert ok.message == "Done"
    assert ok.data["count"] == 2

    redir = ActionResult.redirect("/admin/order")
    assert redir.kind == "redirect"
    assert redir.url == "/admin/order"

    dl = ActionResult.download("orders.csv", "a,b\n1,2\n", "text/csv")
    assert dl.kind == "download"
    assert dl.filename == "orders.csv"
    assert dl.content == "a,b\n1,2\n"

    danger = ActionResult.danger("Nope", errors=[{"id": "3", "error": "missing"}])
    assert danger.kind == "danger"
    assert danger.errors == [{"id": "3", "error": "missing"}]


def test_result_to_schema_is_json_safe():
    schema = ActionResult.ok("hi", errors=[{"id": "1", "error": "x"}]).to_schema()
    assert schema["kind"] == "message"
    assert schema["message"] == "hi"
    assert schema["errors"][0]["id"] == "1"


# --- Prompt ---------------------------------------------------------------


def test_prompt_clean_text_required_and_default():
    required = Prompt("note", "Note", required=True)
    with pytest.raises(BadRequest):
        required.clean("")
    assert required.clean(" hello ") == "hello"
    assert Prompt("kind", default="auto").clean(None) == "auto"


def test_prompt_clean_select_and_boolean_and_number():
    select = Prompt("mode", choices=("fast", "slow"))
    assert select.clean("fast") == "fast"
    with pytest.raises(BadRequest):
        select.clean("bogus")
    assert Prompt("flag", kind="boolean").clean("yes") is True
    assert Prompt("flag", kind="boolean").clean("0") is False
    assert Prompt("count", kind="number").clean("3") == 3
    with pytest.raises(BadRequest):
        Prompt("count", kind="number").clean("abc")


def test_prompt_to_dict():
    d = Prompt("mode", "Mode", kind="select", choices=("a", "b")).to_dict()
    assert d == {"name": "mode", "label": "Mode", "kind": "select", "choices": ["a", "b"], "required": False}


# --- Action orchestration -------------------------------------------------


class EchoAction(Action):
    name = "echo"
    label = "Echo"
    confirmation = "Echo the selected records?"

    async def handle(self, ids, params, context):
        return ActionResult.ok("echoed", data={"ids": list(ids), "params": dict(params)})


@pytest.mark.asyncio
async def test_action_run_cleaned_prompts_and_audit():
    action = EchoAction()
    action.prompts = [Prompt("note", required=True)]
    dash = FakeDashboard()
    result = await _run(action, ["1", "2"], {"note": " hi "}, dash)
    assert result.data["params"]["note"] == "hi"
    assert dash.activities and dash.activities[-1]["action"] == "action"
    assert dash.activities[-1]["details"]["count"] == 2
    assert dash.activities[-1]["details"]["action"] == "echo"


@pytest.mark.asyncio
async def test_action_run_scope_single_and_standalone():
    single = EchoAction()
    single.scope = SINGLE
    with pytest.raises(BadRequest):
        await _run(single, ["1", "2"])
    assert (await _run(single, ["1"])).data["ids"] == ["1"]

    standalone = EchoAction()
    standalone.scope = STANDALONE
    assert (await _run(standalone, [])).data["ids"] == []


@pytest.mark.asyncio
async def test_action_run_bulk_cap_uses_config():
    dash = FakeDashboard(limit=2)
    with pytest.raises(BadRequest):
        await _run(EchoAction(), ["1", "2", "3"], dashboard=dash)


@pytest.mark.asyncio
async def test_action_run_max_records_tighter_than_config():
    action = EchoAction()
    action.max_records = 1
    with pytest.raises(BadRequest):
        await _run(action, ["1", "2"], dashboard=FakeDashboard(limit=50))


@pytest.mark.asyncio
async def test_action_run_can_run_denied_has_no_side_effects():
    class Guarded(EchoAction):
        async def can_run(self, user, dashboard, **kwargs):
            return False

    dash = FakeDashboard()
    with pytest.raises(Forbidden):
        await _run(Guarded(), ["1"], dashboard=dash)
    assert dash.activities == []  # no audit entry, no handle execution


@pytest.mark.asyncio
async def test_action_run_permission_hook():
    class Perm(EchoAction):
        permission = "order.approve_order"

    allowed = FakeDashboard(allowed={"order.approve_order"})
    assert (await _run(Perm(), ["1"], dashboard=allowed)).kind == "message"
    denied = FakeDashboard(allowed=set())
    with pytest.raises(Forbidden):
        await _run(Perm(), ["1"], dashboard=denied)


@pytest.mark.asyncio
async def test_action_run_background_enqueues_without_executing():
    class Bg(EchoAction):
        background = True

    dash = FakeDashboard()
    result = await _run(Bg(), ["1", "2"], {"note": "x"}, dash)
    assert "Queued" in result.message
    assert dash.job_store.queued and dash.job_store.queued[0]["name"] == "admin.action"
    assert dash.job_store.queued[0]["payload"]["action"] == "echo"
    assert dash.job_worker.handlers or dash.job_store.handlers  # a handler was registered


# --- Examples -------------------------------------------------------------


def _fake_model(records):
    return SimpleNamespace(get_instance=lambda oid: next((r for r in records if r["id"] == oid), None))


@pytest.mark.asyncio
async def test_approve_orders_reports_per_record_failures():
    records = [
        {"id": "1", "status": "pending"},
        {"id": "2", "status": "pending"},
    ]
    admin_model = SimpleNamespace(model=_fake_model(records))
    action = ApproveOrders()
    result = await action.run(
        ["1", "2", "3"],
        {},
        dashboard=FakeDashboard(),
        request=None,
        user=SimpleNamespace(username="admin"),
        model_name="order",
        admin_model=admin_model,
    )
    assert records[0]["status"] == "approved" and records[1]["status"] == "approved"
    assert len(result.errors) == 1 and result.errors[0]["id"] == "3"
    assert "Approved 2" in result.message


@pytest.mark.asyncio
async def test_export_csv_is_formula_injection_safe():
    records = [
        {"id": "1", "reference": "=SUM(A1:A9)", "status": "paid"},
        {"id": "2", "reference": "+cmd", "status": "pending"},
    ]
    admin_model = SimpleNamespace(model=_fake_model(records))
    action = ExportCsv()
    result = await action.run(
        ["1", "2"],
        {},
        dashboard=FakeDashboard(),
        request=None,
        user=SimpleNamespace(username="admin"),
        model_name="order",
        admin_model=admin_model,
    )
    assert result.kind == "download" and result.filename.endswith(".csv")
    rows = list(csv.DictReader(io.StringIO(result.content)))
    assert rows[0]["reference"] == "'=SUM(A1:A9)"
    assert rows[1]["reference"] == "'+cmd"


def test_action_to_schema_is_documentable():
    action = ApproveOrders()
    schema = action.to_schema()
    assert schema["name"] == "approve_orders"
    assert schema["scope"] == BULK
    assert schema["confirmation"]
