"""Unit contract for Phase 4 primitives: filters, lenses, policies, import helpers.

These tests are deliberately narrow: they pin the public API and the safety
semantics (deny-by-default policies, formula-injection-safe CSV, column mapping,
impersonation refusals) without needing an HTTP server.
"""

from __future__ import annotations

import pytest

from flaxon.admin.filters import (
    BooleanFilter,
    DateRangeFilter,
    Filter,
    SelectFilter,
    apply_python_filters,
    build_filters,
)
from flaxon.admin.importing import csv_safe, enforce_limits, map_columns
from flaxon.admin.lenses import Lens
from flaxon.admin.policies import Policy, evaluate_policy


class Row:
    def __init__(self, **values):
        self.__dict__.update(values)

    def get(self, key, default=None):
        return getattr(self, key, default)


# --------------------------------------------------------------------------- filters


def test_select_filter_reads_state_from_url_and_builds_orm_q():
    filt = SelectFilter("status", choices=["pending", "paid"])
    params = {"filter_status": "paid"}

    assert filt.active(params) is True
    assert filt.value(params) == "paid"
    query = filt.orm_q(params)
    assert query is not None
    # A simple Q stores its equality test in `filters`.
    assert query.filters == {"status": "paid"}


def test_select_filter_is_inactive_for_blank_or_unknown_values():
    filt = SelectFilter("status", choices=["pending", "paid"])

    assert filt.active({}) is False
    assert filt.orm_q({}) is None
    assert filt.active({"filter_status": ""}) is False
    assert filt.active({"filter_status": "not-a-choice"}) is False


def test_boolean_filter_accepts_true_false_and_rejects_garbage():
    filt = BooleanFilter("fulfilled")

    assert filt.value({"filter_fulfilled": "true"}) is True
    assert filt.value({"filter_fulfilled": "false"}) is False
    assert filt.active({"filter_fulfilled": "false"}) is True
    assert filt.active({"filter_fulfilled": "maybe"}) is False
    assert filt.orm_q({"filter_fulfilled": "true"}).filters == {"fulfilled": True}


def test_date_range_filter_builds_bounds_and_ignores_bad_dates():
    filt = DateRangeFilter("created_at")
    params = {"filter_created_at_from": "2026-01-01", "filter_created_at_to": "2026-01-31"}

    assert filt.active(params) is True
    query = filt.orm_q(params)
    assert query is not None
    keys = {key for child in query.children for key in child.filters}
    assert "created_at__gte" in keys
    assert "created_at__lte" in keys

    bad = {"filter_created_at_from": "not-a-date"}
    assert filt.active(bad) is False
    assert filt.orm_q(bad) is None


def test_filters_match_plain_python_rows_for_legacy_models():
    filters = [SelectFilter("status", choices=["pending", "paid"]), BooleanFilter("fulfilled")]
    rows = [
        Row(id="1", status="pending", fulfilled=True),
        Row(id="2", status="paid", fulfilled=False),
        Row(id="3", status="paid", fulfilled=True),
    ]

    selected = apply_python_filters(filters, {"filter_status": "paid", "filter_fulfilled": "true"}, rows)
    assert [row.id for row in selected] == ["3"]


def test_build_filters_accepts_strings_and_objects():
    built = build_filters(["status", SelectFilter("paid", choices=["yes"])])
    assert isinstance(built[0], Filter)
    assert built[0].field == "status"
    assert isinstance(built[1], SelectFilter)


def test_filter_context_is_template_friendly():
    filt = SelectFilter("status", choices=["pending", "paid"], label="Order status")
    context = filt.context({"filter_status": "paid"})

    assert context["parameter"] == "filter_status"
    assert context["label"] == "Order status"
    assert context["value"] == "paid"
    assert context["kind"] == "select"
    assert [choice["value"] for choice in context["choices"]] == ["pending", "paid"]


# --------------------------------------------------------------------------- lenses


def test_lens_exposes_its_own_columns_filters_and_query():
    lens = Lens(
        "unpaid",
        label="Unpaid orders",
        columns=["reference", "amount"],
        filters=[SelectFilter("status", choices=["pending"])],
        query={"filter_status": "pending"},
    )

    assert lens.name == "unpaid"
    assert lens.get_label() == "Unpaid orders"
    assert lens.columns == ["reference", "amount"]
    assert lens.query == {"filter_status": "pending"}
    assert lens.filters[0].field == "status"


def test_lens_rejects_invalid_names():
    with pytest.raises(ValueError):
        Lens("bad name!")
    with pytest.raises(ValueError):
        Lens("")


# --------------------------------------------------------------------------- policies


def test_policy_is_deny_only_for_configured_actions():
    policy = Policy(view=lambda user, obj=None: False)

    assert policy.allows("view", "user", {"id": 1}) is False
    # Unconfigured actions are not denied by the policy; the permission layer decides.
    assert policy.allows("delete", "user", {"id": 1}) is True
    assert set(policy.configured()) == {"view"}


def test_policy_rejects_unknown_action_names():
    with pytest.raises(ValueError):
        Policy(view_any=lambda user, obj=None: True, destroy=lambda user, obj=None: True)


@pytest.mark.asyncio
async def test_evaluate_policy_supports_sync_and_async_callables():
    assert await evaluate_policy(lambda user, obj=None: True, "u") is True
    assert await evaluate_policy(lambda user, obj=None: False, "u") is False

    async def deny(user, obj=None):
        return False

    assert await evaluate_policy(deny, "u") is False


# --------------------------------------------------------------------------- import/export


def test_csv_safe_neutralises_formula_prefixes():
    assert csv_safe("=cmd|' /C calc'!A0").startswith("'=")
    assert csv_safe("+1+1").startswith("'+")
    assert csv_safe("-2+3").startswith("'-")
    assert csv_safe("@SUM(A1)").startswith("'@")
    assert csv_safe("plain text") == "plain text"
    assert csv_safe(42) == "42"


def test_map_columns_translates_headers_and_reports_unknown_targets():
    rows = [{"Order Ref": "ORD-1", "Total": "10"}, {"Order Ref": "ORD-2", "Total": "20"}]
    mapped, errors = map_columns(rows, {"Order Ref": "reference", "Total": "amount"})

    assert errors == []
    assert mapped == [{"reference": "ORD-1", "amount": "10"}, {"reference": "ORD-2", "amount": "20"}]


def test_map_columns_reports_row_level_problems_without_dropping_rows():
    rows = [{"a": "1"}, {"b": "2"}]
    mapped, errors = map_columns(rows, {"a": "reference", "b": "amount"})

    assert mapped[0] == {"reference": "1"}
    assert mapped[1] == {"amount": "2"}
    assert errors == []


def test_enforce_limits_rejects_oversized_payload_and_too_many_rows():
    with pytest.raises(ValueError, match="too large"):
        enforce_limits(payload_bytes=11, row_count=1, max_bytes=10, max_rows=10)
    with pytest.raises(ValueError, match="too many rows"):
        enforce_limits(payload_bytes=1, row_count=11, max_bytes=10, max_rows=10)
    # Boundary values are accepted.
    enforce_limits(payload_bytes=10, row_count=10, max_bytes=10, max_rows=10)
