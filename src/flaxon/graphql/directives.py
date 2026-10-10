from __future__ import annotations

from typing import Any


class Directive:
    """Directive implementation for the graphql subsystem."""

    def __init__(
        self,
        name: str,
        description: str | None = None,
        locations: list[str] | None = None,
        args: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.locations = locations or []
        self.args = args or {}

    def apply(self, context: Any, args: dict[str, Any]) -> bool:
        """Perform the apply operation for directive."""
        return True


class SkipDirective(Directive):
    """Skip directive implementation for the graphql subsystem."""

    def __init__(self) -> None:
        super().__init__(
            name="skip",
            description="Skip this field if `if` is true.",
            locations=["FIELD", "FRAGMENT_SPREAD", "INLINE_FRAGMENT"],
            args={"if": {"type": "Boolean!", "description": "Skip if true"}},
        )

    def apply(self, context: Any, args: dict[str, Any]) -> bool:
        """Perform the apply operation for skip directive."""
        return not args.get("if", False)


class IncludeDirective(Directive):
    """Include directive implementation for the graphql subsystem."""

    def __init__(self) -> None:
        """Perform the   init   operation for include directive."""
        super().__init__(
            name="include",
            description="Include this field if `if` is true.",
            locations=["FIELD", "FRAGMENT_SPREAD", "INLINE_FRAGMENT"],
            args={"if": {"type": "Boolean!", "description": "Include if true"}},
        )

    def apply(self, context: Any, args: dict[str, Any]) -> bool:
        """Perform the apply operation for include directive."""
        return args.get("if", False)


class DeprecatedDirective(Directive):
    """Deprecated directive implementation for the graphql subsystem."""

    def __init__(self) -> None:
        super().__init__(
            name="deprecated",
            description="Deprecate this field.",
            locations=["FIELD_DEFINITION", "ENUM_VALUE"],
            args={
                "reason": {
                    "type": "String",
                    "description": "Deprecation reason",
                    "default": "No longer supported",
                }
            },
        )


class DeferDirective(Directive):
    """Defer directive implementation for the graphql subsystem."""

    def __init__(self) -> None:
        super().__init__(
            name="defer",
            description="Defer this field's resolution.",
            locations=["FIELD"],
            args={"if": {"type": "Boolean!", "description": "Defer if true"}},
        )


skip_directive = SkipDirective()
include_directive = IncludeDirective()
deprecated_directive = DeprecatedDirective()
defer_directive = DeferDirective()
