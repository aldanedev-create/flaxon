"""`flaxon generate`: every generated component must import, and the useful ones must work."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from flaxon import Flaxon
from flaxon.cli.main import main
from flaxon.db import Model
from flaxon.testing import TestClient
from flaxon.validation import ValidationError

KINDS = ["controller", "schema", "service", "middleware", "model", "task"]


def generate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str, name: str = "Billing") -> Path:
    monkeypatch.setattr(sys, "argv", ["flaxon", "generate", kind, name, "--path", str(tmp_path)])
    assert main() == 0
    return tmp_path / f"{name}_{kind}.py"


def load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"generated_{path.stem}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("kind", KINDS)
def test_every_generated_component_is_importable(monkeypatch, tmp_path, kind):
    path = generate(monkeypatch, tmp_path, kind)
    assert path.is_file(), f"expected {path.name}"
    load(path)


def test_controller_item_route_matches(monkeypatch, tmp_path):
    module = load(generate(monkeypatch, tmp_path, "controller"))
    app = Flaxon("generated")
    app.include_router(module.router)
    client = TestClient(app)
    assert client.get("/api/Billing/").status_code == 200
    item = client.get("/api/Billing/5")
    assert item.status_code == 200
    assert item.json() == {"id": 5, "name": "Billing"}
    assert client.post("/api/Billing/", json_data={"a": 1}).json()["created"] is True


def test_schema_validates_input(monkeypatch, tmp_path):
    schema = load(generate(monkeypatch, tmp_path, "schema")).CreateBilling
    assert schema.load({"name": "Ada", "email": "ada@example.com", "age": 30}).to_dict()["name"] == "Ada"
    with pytest.raises(ValidationError):
        schema.load({"name": "A", "email": "not-an-email", "age": 3})


def test_model_is_an_orm_model(monkeypatch, tmp_path):
    model = load(generate(monkeypatch, tmp_path, "model")).Billing
    assert issubclass(model, Model)
    assert {"id", "name", "created_at", "updated_at"} <= set(model._meta.fields_map)


@pytest.mark.parametrize("kind", KINDS)
def test_generating_twice_does_not_overwrite(monkeypatch, tmp_path, kind):
    path = generate(monkeypatch, tmp_path, kind)
    path.write_text("# mine\n")
    monkeypatch.setattr(sys, "argv", ["flaxon", "generate", kind, "Billing", "--path", str(tmp_path)])
    assert main() == 1
    assert path.read_text() == "# mine\n"
