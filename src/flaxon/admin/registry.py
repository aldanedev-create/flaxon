from __future__ import annotations

import inspect
from typing import Any

from flaxon._imports import import_attribute


class AdminModel:
    """Admin model implementation for the admin subsystem."""

    def __init__(
        self,
        model: Any,
        *,
        list_display: list[str] | None = None,
        list_filter: list[str] | None = None,
        search_fields: list[str] | None = None,
        fields: list[str] | None = None,
        readonly_fields: list[str] | None = None,
        ordering: list[str] | None = None,
        name: str | None = None,
        icon: str | None = None,
        actions: dict[str, Any] | list[Any] | tuple[Any, ...] | None = None,
        can_view: Any | None = None,
        can_add: Any | None = None,
        can_change: Any | None = None,
        can_delete: Any | None = None,
        validate_import: Any | None = None,
        queryset: Any | None = None,
        fieldsets: dict[str, list[str]] | None = None,
        widgets: dict[str, str] | None = None,
        inlines: dict[str, Any] | None = None,
    ) -> None:
        self.fieldsets = fieldsets or {}
        self.widgets = widgets or {}
        self.inlines = inlines or {}
        self.queryset = queryset
        self.model = model
        self.list_display = list_display or ["__str__"]
        self.list_filter = list_filter or []
        self.search_fields = search_fields or []
        self.fields = fields or []
        self.readonly_fields = readonly_fields or []
        self.ordering = ordering or []
        self._name = name or model.__name__.lower()
        self.icon = icon
        self.actions = {}
        self.permission_hooks = {
            "read": can_view,
            "create": can_add,
            "update": can_change,
            "delete": can_delete,
        }
        self.validate_import = validate_import
        if isinstance(actions, dict):
            self.actions.update(actions)
        elif actions:
            for action in actions:
                action_name = getattr(action, "_admin_action", None) or getattr(action, "__name__", "action")
                self.actions[action_name] = action

    def get_name(self) -> str:
        """Return the name."""
        return self._name

    def get_verbose_name(self) -> str:
        """Return the verbose name."""
        return self.model.__name__

    def get_verbose_name_plural(self) -> str:
        """Return the verbose name plural."""
        return f"{self.get_verbose_name()}s"

    def add_action(self, name: str, func: Any) -> None:
        """Add the action."""
        self.actions[name] = func

    def get_actions(self) -> dict[str, Any]:
        """Return the actions."""
        return self.actions

    def get_permission_hook(self, action: str) -> Any | None:
        """Return the permission hook."""
        return self.permission_hooks.get(action)

    @staticmethod
    def display_value(obj: Any, field: Any) -> Any:
        """Resolve a list column like Flask-Admin's ``column_formatters``."""
        if callable(field):
            return field(obj)
        if field == "__str__":
            return str(obj)
        value = obj.get(field, "") if isinstance(obj, dict) else getattr(obj, field, "")
        return value() if callable(value) else value


class Registry:
    """Registry implementation for the admin subsystem."""

    def __init__(self) -> None:
        self._models: dict[str, AdminModel] = {}
        self._model_classes: dict[Any, str] = {}

    def register(self, model: Any, **options: Any) -> None:
        """Perform the register operation for registry."""
        original = model
        model_type = import_attribute("tortoise.models", "Model")

        if isinstance(model, type) and issubclass(model, model_type):
            model_adapter = import_attribute("flaxon.db.admin", "model_adapter")

            model = model_adapter(model, options)
        if hasattr(model, "orm_model"):
            model.registry = self
        admin_model = AdminModel(model, **options)
        self._models[admin_model.get_name()] = admin_model
        self._model_classes[model] = admin_model.get_name()
        self._model_classes[original] = admin_model.get_name()

    def unregister(self, model: Any) -> None:
        """Perform the unregister operation for registry."""
        name = self._model_classes.pop(model, None)
        if name:
            self._models.pop(name, None)

    def get(self, name: str) -> AdminModel | None:
        """Retrieve the requested value using this object's configured behavior."""
        return self._models.get(name)

    def get_by_model(self, model: Any) -> AdminModel | None:
        """Return the by model."""
        name = self._model_classes.get(model)
        return self._models.get(name) if name else None

    def get_all(self) -> list[AdminModel]:
        """Return all matching stored entries."""
        return list(self._models.values())

    def clear(self) -> None:
        """Remove the stored entries."""
        self._models.clear()
        self._model_classes.clear()

    def __len__(self) -> int:
        return len(self._models)


# Global default registry instance for decorators and automatic registration
default_registry = Registry()


async def evaluate_permission_hook(hook, user, target=None):
    """Support both model hooks (user) and object hooks (user, object)."""
    if hook is None:
        return True

    signature = inspect.signature(hook)
    if target is None:
        try:
            signature.bind(user)
        except TypeError:
            # A required object hook is evaluated per record, not against None.
            return True
        result = hook(user)
    else:
        try:
            signature.bind(user, target)
        except TypeError:
            result = hook(user)
        else:
            result = hook(user, target)
    return bool(await result if inspect.isawaitable(result) else result)
