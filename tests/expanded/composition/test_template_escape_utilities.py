"""Template escape utilities behavior and boundary cases."""

import pytest

from flaxon.jinax.escaping import Escaper, escape, mark_safe


@pytest.mark.parametrize("value", ["<script>", "a&b", '"quoted"', "'quoted'", ""])
def test_html_escape_roundtrip(value):
    assert Escaper.unescape_html(Escaper.escape_html(value)) == value


@pytest.mark.parametrize("value", ["a b", "café", "a/b?c=d", "<script>"])
def test_url_escape_roundtrip(value):
    encoded = Escaper.escape_url(value)
    assert Escaper.unescape_url(encoded) == value
    assert " " not in encoded and "<" not in encoded


def test_css_punctuation_is_escaped():
    assert Escaper.escape_css("a b#") == "a\\20 b\\23 "


def test_safe_string_requires_explicit_marking():
    assert escape("<b>safe?</b>") == "&lt;b&gt;safe?&lt;/b&gt;"
    assert escape(mark_safe("<b>trusted</b>")) == "<b>trusted</b>"
    assert escape(None) == ""
