"""Migration sql boundaries behavior and boundary cases."""

import pytest

from flaxon.database.migrations import _sql_statements


@pytest.mark.parametrize(
    "script,expected",
    [
        ("SELECT 1; SELECT 2;", ["SELECT 1", "SELECT 2"]),
        ("SELECT ';'; SELECT 2", ["SELECT ';'", "SELECT 2"]),
        ("INSERT INTO t VALUES ('it''s;a');", ["INSERT INTO t VALUES ('it''s;a')"]),
        ('SELECT "a;b"; SELECT `x;y`;', ['SELECT "a;b"', "SELECT `x;y`"]),
        (" ; ; ", []),
    ],
)
def test_semicolons_inside_quoted_values_do_not_split(script, expected):
    assert _sql_statements(script) == expected


def test_final_statement_without_terminator_is_preserved():
    assert _sql_statements("SELECT 1;\n SELECT 2") == ["SELECT 1", "SELECT 2"]
