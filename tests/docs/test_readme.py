"""The README is documentation we promise works: run its code, check its claims, check its links."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest

from flaxon.cli.main import create_parser
from flaxon.cli.project_templates import template_names
from flaxon.testing import TestClient

ROOT = Path(__file__).resolve().parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8")
GITHUB = "https://github.com/aldanedev-create/flaxon/"
RAW = "https://raw.githubusercontent.com/aldanedev-create/flaxon/main/"


def blocks(language: str) -> list[str]:
    return re.findall(rf"```{language}\n(.*?)```", README, re.S)


def readme_app(index: int = 0):
    pytest.importorskip("pydantic")
    namespace: dict[str, object] = {"__name__": "readme_main"}
    exec(compile(blocks("python")[index], "README.md", "exec"), namespace)
    return namespace["app"]


# --- the code in the README works, and its documented output is real -----------------------------


def test_documented_check_output_matches_the_real_response():
    client = TestClient(readme_app())
    expected = json.loads(blocks("json")[0])
    assert client.get("/items/5", query={"q": "somequery"}).json() == expected


def test_documented_validation_error_matches_the_real_response():
    client = TestClient(readme_app())
    response = client.post("/items", json_data={"name": "Pen"})
    assert response.status_code == 422
    assert response.json() == json.loads(blocks("json")[1])


def test_example_endpoints_and_interactive_docs_work():
    client = TestClient(readme_app())
    assert client.get("/").json() == {"message": "Hello, Flaxon"}
    created = client.post("/items", json_data={"name": "Pen", "price": 1.5})
    assert created.status_code == 200
    assert created.json() == {"created": {"name": "Pen", "price": 1.5, "in_stock": True}}
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 200, path
    assert "/items" in client.get("/openapi.json").json()["paths"]


def test_example_upgrade_adds_a_working_put_and_keeps_the_original_endpoints():
    client = TestClient(readme_app(1))
    updated = client.put("/items/5", json_data={"name": "Pen", "price": 1.5, "in_stock": False})
    assert updated.status_code == 200
    assert updated.json() == {"item_id": 5, "item_name": "Pen", "in_stock": False}
    assert client.put("/items/5", json_data={"name": "Pen"}).status_code == 422
    assert client.get("/items/5", query={"q": "x"}).json() == {"item_id": 5, "q": "x"}
    assert client.post("/items", json_data={"name": "Pen", "price": 1.5}).status_code == 200
    put = client.get("/openapi.json").json()["paths"]["/items/{item_id}"]["put"]
    assert "requestBody" in put and [p["name"] for p in put["parameters"]] == ["item_id"]


# --- the commands, templates and extras it mentions exist --------------------------------------


def test_every_flaxon_command_in_the_readme_exists():
    subcommands = create_parser()._subparsers._group_actions[0].choices
    seen = set()
    for block in blocks("bash"):
        for line in block.splitlines():
            match = re.match(r"\s*flaxon (\w[\w-]*)", line)
            if match:
                seen.add(match.group(1))
    assert seen, "expected flaxon commands in the README"
    assert seen <= set(subcommands), f"unknown commands: {seen - set(subcommands)}"
    # also the commands in the table of "other commands worth knowing"
    for name in re.findall(r"`flaxon (\w+)", README):
        assert name in subcommands, name


def test_every_template_named_in_the_readme_exists():
    named = set(re.findall(r"--template ([a-z][\w-]*)", README))  # uppercase = placeholder
    named |= set(re.findall(r"^\| `([\w-]+)`(?: \(default\))? \| ", README, re.M)) & {"basic", "fullstack"}
    assert named <= set(template_names()), named - set(template_names())
    for name in template_names():
        assert f"`{name}`" in README, f"template {name} is not documented in the README"


def test_generate_kinds_in_the_readme_exist():
    kinds = set(re.findall(r"flaxon generate (\w+)", README))
    assert kinds == {"controller", "schema", "model", "service", "middleware", "task"}


def test_every_extra_in_the_readme_is_defined():
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["optional-dependencies"]
    named = {name for group in re.findall(r"flaxon\[([\w,-]+)\]", README) for name in group.split(",")}
    assert named <= set(extras), named - set(extras)


# --- links and images point at things that exist -----------------------------------------------


def repo_links() -> list[str]:
    prefixes = "|".join(re.escape(prefix) for prefix in (GITHUB, RAW))
    urls = re.findall(rf'(?:\]\(|href="|src=")((?:{prefixes})[^)"\s#]+)', README)
    return sorted(set(urls))


@pytest.mark.parametrize("url", repo_links())
def test_repository_links_and_images_exist(url):
    for prefix in (RAW, GITHUB + "blob/main/", GITHUB + "tree/main/"):
        if url.startswith(prefix):
            target = ROOT / url.removeprefix(prefix)
            assert target.exists(), f"{url} -> {target} is missing"
            return
    pytest.skip("not a path into the repository (for example the issues page)")


def slug(heading: str) -> str:
    text = re.sub(r"[^\w\s-]", "", heading.lower(), flags=re.UNICODE).strip()
    return re.sub(r"\s", "-", text)


def test_in_page_anchors_resolve():
    headings = {slug(h) for h in re.findall(r"^#{1,6} (.+)$", README, re.M)}
    anchors = set(re.findall(r'\]\(#([^)]+)\)|href="#([^"]+)"', README))
    names = {a or b for a, b in anchors}
    assert names, "expected in-page links"
    assert names <= headings, f"broken anchors: {names - headings}"


def test_readme_keeps_the_original_sections():
    for heading in (
        "Watch the full course",
        "Documentation",
        "Examples",
        "Community and contributing",
        "Publishing releases",
        "Security",
        "License",
    ):
        assert re.search(rf"^#{{2,3}} .*{heading}", README, re.M), heading


def test_dependencies_section_matches_pyproject():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    core = {re.split(r"[<>=!~\[ ]", dep, maxsplit=1)[0].lower() for dep in project["dependencies"]}
    section = README.split("## Dependencies", 1)[1].split("## Learn more", 1)[0]
    intro = section.split("`pip install flaxon` currently installs", 1)[0]
    required = {name.lower() for name in re.findall(r"\*\*([\w-]+)\*\*", intro)} & core
    assert required == {"orjson", "pyjwt", "argon2-cffi"}
    for row in re.findall(r"^\| ((?:`[\w-]+`(?:, )?)+) \|", section, re.M):
        for name in re.findall(r"`([\w-]+)`", row):
            assert name.lower() in core, (
                f"{name} is documented as installed by default but is not a core dependency"
            )
