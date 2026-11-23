"""Per-resource policies: ``view_any``, ``view``, ``create``, ``update``, etc.

The full action set is ``view_any``, ``view``, ``create``, ``update``,
``delete``, ``restore`` and ``force_delete``.

A policy is **deny-only** and additive. Unconfigured actions fall through to
the existing permission system, so registering a policy can only tighten
access — never silently widen it. That keeps legacy registrations safe.

Policy callables receive ``(user, obj)`` or ``(user,)``; both synchronous and
async callables are supported by :func:`evaluate_policy`.
"""

from __future__ import annotations

import inspect
from typing import Any

__all__ = ["POLICY_ACTIONS", "Policy", "evaluate_policy"]

POLICY_ACTIONS = (
    "view_any",
    "view",
    "create",
    "update",
    "delete",
    "restore",
    "force_delete",
)


def _accepts_object(callable_: Any) -> bool:
    try:
        parameters = [
            parameter
            for parameter in inspect.signature(callable_).parameters.values()
            if parameter.kind
            in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD, parameter.VAR_POSITIONAL)
        ]
    except (TypeError, ValueError):  # builtins without a signature
        return True
    return len(parameters) >= 2


async def evaluate_policy(callable_: Any, user: Any, obj: Any = None) -> bool:
    """Evaluate a policy callable, awaiting it when necessary."""
    result = callable_(user, obj) if _accepts_object(callable_) else callable_(user)
    if hasattr(result, "__await__"):
        result = await result
    return bool(result)


class Policy:
    """A deny-only bundle of per-action rules for one resource."""

    def __init__(self, **actions: Any) -> None:
        unknown = set(actions) - set(POLICY_ACTIONS)
        if unknown:
            raise ValueError(
                f"Unknown policy action(s): {', '.join(sorted(unknown))}. "
                f"Valid actions: {', '.join(POLICY_ACTIONS)}"
            )
        self._actions = {name: rule for name, rule in actions.items() if rule is not None}

    def configured(self) -> set[str]:
        """Return the names of the actions this policy actually constrains."""
        return set(self._actions)

    def rule(self, action: str) -> Any | None:
        """Return the callable for ``action``, or ``None`` when unconstrained."""
        return self._actions.get(action)

    def allows(self, action: str, user: Any, obj: Any = None) -> bool:
        """Synchronously evaluate ``action``; unconstrained actions return True."""
        rule = self._actions.get(action)
        if rule is None:
            return True
        result = rule(user, obj) if _accepts_object(rule) else rule(user)
        if hasattr(result, "__await__"):
            raise TypeError("Policy callable is async; use evaluate_policy() instead")
        return bool(result)

    async def allows_async(self, action: str, user: Any, obj: Any = None) -> bool:
        """Evaluate ``action``, supporting async callables."""
        rule = self._actions.get(action)
        if rule is None:
            return True
        return await evaluate_policy(rule, user, obj)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Policy({', '.join(sorted(self._actions))})"
