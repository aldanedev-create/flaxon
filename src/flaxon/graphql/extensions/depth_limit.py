from __future__ import annotations

from typing import Any


class DepthLimitExtension:
    def __init__(self, max_depth: int = 10, enabled: bool = True) -> None:
        self.max_depth = max_depth
        self.enabled = enabled

    def calculate_depth(self, document: Any) -> int:
        max_depth = 0

        for definition in document.definitions:
            if hasattr(definition, "selection_set"):
                depth = self._calculate_selection_set_depth(definition.selection_set)
                if depth > max_depth:
                    max_depth = depth

        return max_depth

    def _calculate_selection_set_depth(self, selection_set: Any, current_depth: int = 0) -> int:
        max_depth = current_depth

        for selection in selection_set.selections:
            if hasattr(selection, "field"):
                if selection.selection_set:
                    depth = self._calculate_selection_set_depth(selection.selection_set, current_depth + 1)
                    if depth > max_depth:
                        max_depth = depth
                else:
                    if current_depth + 1 > max_depth:
                        max_depth = current_depth + 1

            elif hasattr(selection, "inline_fragment"):
                if selection.selection_set:
                    depth = self._calculate_selection_set_depth(selection.selection_set, current_depth + 1)
                    if depth > max_depth:
                        max_depth = depth

            elif hasattr(selection, "fragment_spread"):
                if current_depth + 1 > max_depth:
                    max_depth = current_depth + 1

        return max_depth

    def validate_depth(self, document: Any) -> bool:
        if not self.enabled:
            return True

        depth = self.calculate_depth(document)
        return depth <= self.max_depth

    async def before(self, context: dict[str, Any]) -> None:
        if not self.enabled:
            return

        document = context.get("document")
        if document is None:
            return

        if not self.validate_depth(document):
            raise Exception(
                f"Query depth {self.calculate_depth(document)} exceeds maximum of {self.max_depth}"
            )

    async def after(self, context: dict[str, Any], result: dict[str, Any]) -> None:
        pass
