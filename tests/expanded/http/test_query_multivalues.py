"""Query multivalues behavior and boundary cases."""

import pytest

from flaxon.http.query_params import QueryParams


@pytest.mark.parametrize("query", ["tag=a&tag=b&empty=", b"tag=a&tag=b&empty="])
def test_repeated_values_and_blanks(query):
    params = QueryParams(query)
    assert params.getlist("tag") == ["a", "b"]
    assert params["empty"] == ""
    assert len(params) == 2


def test_encoded_query_values():
    params = QueryParams("city=Kingston+Town&symbol=%26%3D&word=%E6%97%A5%E6%9C%AC")
    assert params["city"] == "Kingston Town"
    assert params["symbol"] == "&="
    assert params["word"] == "日本"


def test_getlist_cannot_modify_mapping():
    params = QueryParams("tag=a")
    params.getlist("tag").append("b")
    assert params.getlist("tag") == ["a"]
