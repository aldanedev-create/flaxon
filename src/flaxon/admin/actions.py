"""Class-based admin actions (Phase 3).

An :class:`Action` bundles a label, prompt fields, a confirmation message, a
scope (single / bulk / standalone), authorization, optional background
execution, a result type (message / redirect / download / danger) and an audit
entry. Actions are additive: the legacy ``register(..., actions=...)`` callables
and ``ContentType.register_action`` keep working unchanged.

The module intentionally has no top-level optional dependency (Tortoise,
Jinja2) imports; everything is reached through the dashboard at run time.
"""

from __future__ import annotations

import csv
import inspect
import io
from dataclasses import dataclass, field
from typing import Any, ClassVar

from flaxon.exceptions import BadRequest, Forbidden

__all__ = [
    "BULK",
    "SINGLE",
    "STANDALONE",
    "Action",
    "ActionContext",
    "ActionResult",
    "ApproveOrders",
    "ExportCsv",
    "Prompt",
]

SINGLE = "single"
BULK = "bulk"
STANDALONE = "standalone"

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value: Any) -> Any:
    """Neutralize spreadsheet formula injection for exported cells."""
    if not isinstance(value, str):
        return value
    return "'" + value if value.lstrip()[:1] in _FORMULA_PREFIXES else value


@dataclass
class ActionResult:
    """Describe the outcome of an action in a transport-independent way."""

    kind: str
    message: str = ""
    url: str | None = None
    filename: str | None = None
    content: str | bytes = ""
    content_type: str = "text/plain; charset=utf-8"
    errors: list[dict[str, Any]] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(
        cls, message: str, *, data: dict[str, Any] | None = None, errors: list[dict[str, Any]] | None = None
    ) -> ActionResult:
        """Build a success/message result."""
        return cls("message", message=message, data=data or {}, errors=errors or [])

    @classmethod
    def redirect(cls, url: str, **kwargs: Any) -> ActionResult:
        """Build a redirect result."""
        return cls("redirect", url=url, **kwargs)

    @classmethod
    def download(
        cls, filename: str, content: str | bytes, content_type: str = "text/csv; charset=utf-8"
    ) -> ActionResult:
        """Build a download result."""
        return cls("download", filename=filename, content=content, content_type=content_type)

    @classmethod
    def danger(cls, message: str, *, errors: list[dict[str, Any]] | None = None) -> ActionResult:
        """Build a danger (failed or partially failed) result."""
        return cls("danger", message=message, errors=errors or [])

    def to_schema(self) -> dict[str, Any]:
        """Return a JSON-safe representation for templates and audit entries."""
        return {
            "kind": self.kind,
            "message": self.message,
            "url": self.url,
            "filename": self.filename,
            "errors": [dict(error) for error in self.errors],
            "data": dict(self.data),
        }


@dataclass
class Prompt:
    """A single field an action asks the operator to fill before running."""

    name: str
    label: str | None = None
    kind: str = "text"
    required: bool = False
    choices: tuple[Any, ...] = ()
    default: Any = None

    def clean(self, raw: Any) -> Any:
        """Validate and coerce a submitted value, raising on invalid input."""
        if raw is None or (isinstance(raw, str) and raw == ""):
            if self.default is not None:
                return self.default
            if self.required:
                raise BadRequest(f"Prompt '{self.name}' is required")
            return None
        if self.kind == "boolean":
            return str(raw).strip().lower() in {"1", "true", "on", "yes"}
        if self.kind == "number":
            try:
                return int(str(raw))
            except ValueError as exc:
                raise BadRequest(f"Prompt '{self.name}' must be a number") from exc
        value = str(raw).strip()
        if self.choices and value not in {str(choice) for choice in self.choices}:
            raise BadRequest(f"Prompt '{self.name}' has an invalid choice")
        return value

    def to_dict(self) -> dict[str, Any]:
        """Return the prompt declaration for schema/template rendering."""
        return {
            "name": self.name,
            "label": self.label or self.name.replace("_", " ").title(),
            "kind": self.kind,
            "choices": list(self.choices),
            "required": self.required,
        }


@dataclass
class ActionContext:
    """Runtime context handed to :meth:`Action.handle`."""

    dashboard: Any
    request: Any
    user: Any
    model_name: str | None
    admin_model: Any
    params: dict[str, Any]


class Action:
    """Base class for a class-based admin action."""

    name: str | None = None
    label: str | None = None
    description: str = ""
    confirmation: str | None = None
    scope: str = BULK
    prompts: ClassVar[list[Prompt]] = []
    background: bool = False
    permission: str | None = None
    max_records: int | None = None

    def get_name(self) -> str:
        """Return the stable registration name for this action."""
        return self.name or type(self).__name__.lower()

    def get_label(self) -> str:
        """Return the human-readable label for this action."""
        return self.label or self.get_name().replace("_", " ").title()

    def to_schema(self) -> dict[str, Any]:
        """Return the action declaration for docs and the admin UI."""
        return {
            "name": self.get_name(),
            "label": self.get_label(),
            "description": self.description,
            "confirmation": self.confirmation,
            "scope": self.scope,
            "prompts": [prompt.to_dict() for prompt in self.prompts],
            "background": self.background,
            "permission": self.permission,
        }

    async def can_run(self, user: Any, dashboard: Any, **kwargs: Any) -> bool:
        """Return whether ``user`` may run this action."""
        if self.permission:
            return bool(await dashboard.auth.has_permission_async(user, self.permission))
        return True

    async def handle(self, ids: list[str], params: dict[str, Any], context: ActionContext) -> ActionResult:
        """Execute the action. Subclasses must override this."""
        raise NotImplementedError

    def _effective_limit(self, dashboard: Any) -> int:
        limit = int(getattr(dashboard.config, "action_bulk_limit", 1000))
        return limit if self.max_records is None else min(limit, int(self.max_records))

    async def run(
        self,
        ids: list[str],
        params: dict[str, Any],
        *,
        dashboard: Any,
        request: Any,
        user: Any,
        model_name: str | None = None,
        admin_model: Any = None,
    ) -> ActionResult:
        """Validate, authorize, execute and audit this action."""
        ids = [str(value) for value in ids]
        if self.scope == SINGLE and len(ids) != 1:
            raise BadRequest("This action applies to exactly one record")
        limit = self._effective_limit(dashboard)
        if len(ids) > limit:
            raise BadRequest(f"Select at most {limit} records per action")
        if not await self.can_run(user, dashboard, request=request, model_name=model_name, ids=ids):
            raise Forbidden("You are not allowed to run this action")

        reserved = {"_csrf", "ids", "action"}
        cleaned: dict[str, Any] = {
            key: value
            for key, value in params.items()
            if key not in reserved and key not in {p.name for p in self.prompts}
        }
        for prompt in self.prompts:
            cleaned[prompt.name] = prompt.clean(params.get(prompt.name))

        if self.background:
            payload = {
                "action": self.get_name(),
                "model": model_name,
                "ids": ids,
                "params": cleaned,
                "actor": getattr(user, "username", "system"),
            }
            dashboard.job_store.enqueue("admin.action", payload)
            worker = getattr(dashboard, "job_worker", None)
            if worker is not None:
                worker.register("admin.action", getattr(dashboard, "run_action_job", self.handle))
            result = ActionResult.ok(f"Queued {self.get_label()} for {len(ids)} record(s).")
        else:
            context = ActionContext(
                dashboard=dashboard,
                request=request,
                user=user,
                model_name=model_name,
                admin_model=admin_model,
                params=cleaned,
            )
            result = await self.handle(ids, cleaned, context)

        dashboard.record_activity(
            "action",
            model_name or "admin",
            request,
            details={
                "action": self.get_name(),
                "count": len(ids),
                "scope": self.scope,
                "result": result.kind,
                "failures": len(result.errors),
            },
        )
        return result


class ApproveOrders(Action):
    """Example bulk action: mark selected orders as approved."""

    name = "approve_orders"
    label = "Approve orders"
    description = "Mark the selected orders as approved."
    confirmation = "Approve the selected orders?"
    scope = BULK

    async def handle(self, ids: list[str], params: dict[str, Any], context: ActionContext) -> ActionResult:
        """Approve each record, collecting per-record failures."""
        model = getattr(context.admin_model, "model", None)
        approved: list[str] = []
        errors: list[dict[str, Any]] = []
        for object_id in ids:
            try:
                obj = model.get_instance(object_id) if model is not None else None
                if inspect.isawaitable(obj):
                    obj = await obj
                if obj is None:
                    raise LookupError(f"Unknown record {object_id}")
                if isinstance(obj, dict):
                    obj["status"] = "approved"
                else:
                    obj.status = "approved"
                approved.append(object_id)
            except Exception as exc:
                errors.append({"id": str(object_id), "error": str(exc)})
        return ActionResult.ok(
            f"Approved {len(approved)} order(s).", data={"approved": approved}, errors=errors
        )


class ExportCsv(Action):
    """Example bulk action: export selected records as injection-safe CSV."""

    name = "export_csv"
    label = "Export CSV"
    description = "Download the selected records as CSV."
    scope = BULK

    async def handle(self, ids: list[str], params: dict[str, Any], context: ActionContext) -> ActionResult:
        """Build a CSV download from the selected records."""
        model = getattr(context.admin_model, "model", None)
        rows: list[dict[str, Any]] = []
        for object_id in ids:
            obj = model.get_instance(object_id) if model is not None else None
            if inspect.isawaitable(obj):
                obj = await obj
            if obj is None:
                continue
            source = dict(obj) if isinstance(obj, dict) else _snapshot(obj)
            rows.append({key: _csv_safe(value) for key, value in source.items()})
        columns = sorted({key for row in rows for key in row})
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return ActionResult.download(f"{context.model_name or 'export'}-export.csv", output.getvalue())


def _snapshot(obj: Any) -> dict[str, Any]:
    """Return a shallow, JSON-safe snapshot of an arbitrary record object."""
    if hasattr(obj, "__dict__"):
        return {key: value for key, value in vars(obj).items() if not key.startswith("_")}
    return {"value": obj}
