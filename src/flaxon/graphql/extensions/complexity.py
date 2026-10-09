from __future__ import annotations

from typing import Any


class ComplexityExtension:
    def __init__(self, max_complexity: int = 100, enabled: bool = True) -> None:
        self.max_complexity = max_complexity
        self.enabled = enabled
        self._costs: dict[str, int] = {}

    def set_cost(self, field_name: str, cost: int) -> None:
        self._costs[field_name] = cost

    def set_costs(self, costs: dict[str, int]) -> None:
        self._costs.update(costs)

    def get_cost(self, field_name: str) -> int:
        return self._costs.get(field_name, 1)

    def calculate_complexity(self, document: Any) -> int:
        complexity = 0

        for definition in document.definitions:
            if hasattr(definition, "selection_set") and definition.selection_set:
                complexity += self._calculate_selection_set(definition.selection_set)

        return complexity

    def _calculate_selection_set(self, selection_set: Any, depth: int = 0) -> int:
        total = 0

        for selection in selection_set.selections:
            if hasattr(selection, "name"):
                field_name = selection.name.value if hasattr(selection.name, "value") else str(selection.name)
                cost = self.get_cost(field_name)

                if getattr(selection, "selection_set", None):
                    total += cost * self._calculate_selection_set(selection.selection_set, depth + 1)
                else:
                    total += cost

            elif getattr(selection, "selection_set", None):
                total += self._calculate_selection_set(selection.selection_set, depth + 1)

            else:
                total += 1

        return total

    def validate_complexity(self, document: Any) -> bool:
        if not self.enabled:
            return True

        complexity = self.calculate_complexity(document)
        return complexity <= self.max_complexity

    async def before(self, context: dict[str, Any]) -> None:
        if not self.enabled:
            return

        document = context.get("document")
        if document is None:
            return

        if not self.validate_complexity(document):
            raise Exception(
                f"Query complexity {self.calculate_complexity(document)} exceeds maximum of {self.max_complexity}"
            )

    async def after(self, context: dict[str, Any], result: dict[str, Any]) -> None:
        pass
