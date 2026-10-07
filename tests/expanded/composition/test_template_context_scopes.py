"""Template context scopes behavior and boundary cases."""

from flaxon.jinax.context import Context, ContextStack


def test_child_can_shadow_parent_without_mutating_it():
    parent = Context()
    parent.update({"name": "parent", "shared": 1})
    child = parent.push()
    child["name"] = "child"
    assert child.to_dict() == {"name": "child", "shared": 1}
    assert parent["name"] == "parent"
    assert child.pop() is parent


def test_context_stack_restores_outer_scope_on_pop():
    stack = ContextStack()
    stack.set("value", 1)
    stack.push()
    stack.set("value", 2)
    assert stack.get("value") == 2
    stack.pop()
    assert stack.get("value") == 1
    assert stack.pop() is None
    assert stack.get("missing", "fallback") == "fallback"


def test_flattened_context_does_not_expose_internal_mapping():
    context = Context()
    context.set("value", 1)
    flat = context.to_dict()
    flat["value"] = 2
    assert context.get("value") == 1
