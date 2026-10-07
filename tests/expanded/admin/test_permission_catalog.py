"""Permission catalog behavior and boundary cases."""

import pytest

from flaxon.admin.authorization import PermissionCatalog, canonical_model_permission


@pytest.mark.parametrize(
    "action,verb", [("read", "view"), ("create", "add"), ("update", "change"), ("delete", "delete")]
)
def test_catalog_resolves_legacy_model_aliases(action, verb):
    catalog = PermissionCatalog()
    catalog.register_model("jobs", "Jobs")
    assert catalog.resolve("jobs:" + action) == f"jobs.{verb}_jobs"
    assert canonical_model_permission("jobs", action) == f"jobs.{verb}_jobs"


def test_destructive_capabilities_are_marked_dangerous():
    catalog = PermissionCatalog()
    catalog.register_model("jobs")
    assert catalog.get("jobs.delete_jobs").dangerous
    assert not catalog.get("jobs.view_jobs").dangerous


def test_catalogs_do_not_share_application_registrations():
    first = PermissionCatalog()
    first.register_model("jobs")
    assert PermissionCatalog().get("jobs.view_jobs") is None
