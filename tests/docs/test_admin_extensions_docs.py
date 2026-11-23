"""Docs-as-contract: every Python block in the admin extensions guide executes."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "guides" / "admin-extensions.md"
BLOCKS = re.findall(r"```python\n(.*?)```", DOC.read_text(encoding="utf-8"), re.S)

PLUGIN_ROOT = str(ROOT / "examples" / "flaxon_admin_rating")
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)


def _run_all():
    namespace = {"__name__": "admin_extensions_docs"}
    for index, block in enumerate(BLOCKS, start=1):
        exec(compile(block, f"admin-extensions.md:block-{index}", "exec"), namespace)
    return namespace


def test_guide_has_five_executable_examples():
    assert len(BLOCKS) == 5


def test_custom_field_example_is_about_twenty_lines():
    code = BLOCKS[0]
    assert len([line for line in code.splitlines() if line.strip()]) <= 21
    namespace = _run_all()
    field = namespace["SentimentField"]("sentiment")
    assert field.component.name == "sentiment"
    assert field.schema_entry()["fallback_choices"] == [
        ["happy", "Happy"],
        ["neutral", "Neutral"],
        ["sad", "Sad"],
    ]


def test_field_is_usable_in_a_resource():
    namespace = _run_all()
    resource = namespace["FeedbackResource"]()
    assert [field.name for field in resource.fields] == ["comment", "sentiment"]
    assert resource.fields[1].is_sortable is True


def test_card_page_and_tool_examples_are_consistent():
    namespace = _run_all()
    extension = namespace["AnalyticsExtension"]()
    assert extension.name == "analytics"
    page = extension.pages()[0]
    assert page.permission == "admin.view_reports"
    tool = extension.tools()[0]
    assert tool.url == "reports"


def test_configuration_example_matches_the_real_config():
    namespace = _run_all()
    config = namespace["config"]
    assert config.enable_extensions is True
    assert config.disabled_extensions == ("analytics",)


def test_example_plugin_claim_is_true():
    namespace = _run_all()
    assert namespace["extension"].name == "rating"
    assert namespace["RatingField"]("rating").component.name == "rating"


def test_api_reference_is_generated_from_code():
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import generate_admin_extension_docs  # noqa: PLC0415 - local script

    assert generate_admin_extension_docs.OUTPUT.read_text(encoding="utf-8") == (
        generate_admin_extension_docs.render()
    )
