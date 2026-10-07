"""Session mutation tracking behavior and boundary cases."""

from flaxon.sessions.session import Session


def test_mutations_mark_dirty_and_clean_can_be_reset():
    session = Session(data={"a": 1})
    assert not session.is_dirty()
    session["a"] = 2
    assert session.is_dirty()
    session.mark_clean()
    assert not session.is_dirty()
    session.update({"b": 3})
    assert session.is_dirty()
    assert session.to_dict() == {"a": 2, "b": 3}


def test_existing_setdefault_does_not_dirty_session():
    session = Session(data={"a": 1})
    assert session.setdefault("a", 2) == 1
    assert not session.is_dirty()
    assert session.setdefault("b", 2) == 2
    assert session.is_dirty()


def test_pop_delete_and_clear_update_data():
    session = Session(data={"a": 1, "b": 2})
    assert session.pop("a") == 1
    del session["b"]
    assert session.to_dict() == {}
    session.update({"c": 3})
    session.clear()
    assert session.keys() == []


def test_to_dict_does_not_expose_top_level_mapping():
    session = Session(data={"a": 1})
    snapshot = session.to_dict()
    snapshot["a"] = 99
    assert session["a"] == 1
