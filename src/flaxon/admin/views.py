from __future__ import annotations

import json
from typing import Any

from flaxon.http import HTMLResponse, RedirectResponse, Request
from flaxon.exceptions import Conflict

class AdminView:
    def __init__(self, admin_model: Any, request: Request, dashboard: Any) -> None:
        self.admin_model = admin_model
        self.request = request
        self.dashboard = dashboard

    async def render(self) -> HTMLResponse | RedirectResponse:
        raise NotImplementedError

    @staticmethod
    def _form_dict(form: Any) -> dict[str, Any]:
        """Normalize framework FormData and test/client dictionaries alike."""

        if hasattr(form, "to_dict"):
            return form.to_dict()
        if isinstance(form, dict):
            return dict(form)
        return dict(form or {})


class ChangeListView(AdminView):
    async def render(self) -> HTMLResponse:
        model_class = self.admin_model.model
        objects: list[Any] = []
        page = max(1, int(self.request.query.get("page", "1") or 1))
        per_page = min(200, max(1, int(self.request.query.get("per_page", "25") or 25)))
        query_result = None
        if hasattr(model_class, "query"):
            result = model_class.query(q=self.request.query.get("q") or None, page=page, per_page=per_page)
            query_result = await result if hasattr(result, "__await__") else result
            objects = list(query_result.get("items", []))
        elif hasattr(model_class, "get_instances"):
            result = model_class.get_instances()
            objects = list(await result if hasattr(result, "__await__") else result)
            needle = self.request.query.get("q", "").lower()
            if needle:
                fields = self.admin_model.search_fields or self.admin_model.fields
                objects = [obj for obj in objects if any(needle in str((obj.get(f) if isinstance(obj, dict) else getattr(obj, f, ""))).lower() for f in fields)]
            for field in self.admin_model.list_filter:
                value = self.request.query.get(f"filter_{field}", "")
                if value:
                    objects = [obj for obj in objects if str((obj.get(field) if isinstance(obj, dict) else getattr(obj, field, ""))) == value]
            ordering = self.request.query.get("order_by")
            if ordering:
                reverse = ordering.startswith("-")
                key = ordering.lstrip("-")
                objects.sort(key=lambda obj: (obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)), reverse=reverse)
            total = len(objects)
            objects = objects[(page - 1) * per_page : page * per_page]
            query_result = {"total": total, "pages": max(1, (total + per_page - 1) // per_page), "page": page, "per_page": per_page}

        # Object-level read rules are applied after the adapter query so
        # custom Admin models can keep their data source unchanged.
        hook = self.admin_model.get_permission_hook("read")
        if hook is not None:
            visible = []
            for obj in objects:
                allowed = hook(getattr(self.request, "user", None), obj)
                allowed = await allowed if hasattr(allowed, "__await__") else allowed
                if allowed:
                    visible.append(obj)
            objects = visible

        context = {
            "model": self.admin_model,
            "models": self.dashboard.registry.get_all(),
            "objects": objects,
            "verbose_name": self.admin_model.get_verbose_name(),
            "verbose_name_plural": self.admin_model.get_verbose_name_plural(),
            "list_display": self.admin_model.list_display,
            "list_filter": self.admin_model.list_filter,
            "search_fields": self.admin_model.search_fields,
            "actions": {
                name: action for name, action in self.admin_model.get_actions().items()
                if self._can_action(name)
            },
            "user": getattr(self.request, "user", None),
            "request": self.request,
            "query": self.request.query.get("q", ""),
            "pagination": query_result or {"total": len(objects), "pages": 1, "page": 1, "per_page": len(objects)},
            "can_add": self.dashboard.can_access_model(getattr(self.request, "user", None), self.admin_model.get_name(), "create"),
            "can_change": self.dashboard.can_access_model(getattr(self.request, "user", None), self.admin_model.get_name(), "update"),
            "can_delete": self.dashboard.can_access_model(getattr(self.request, "user", None), self.admin_model.get_name(), "delete"),
            "can_import": self.dashboard.can_access_model(getattr(self.request, "user", None), self.admin_model.get_name(), "create"),
            "can_export": self.dashboard.can_access_model(getattr(self.request, "user", None), self.admin_model.get_name(), "read"),
        }
        return await self.dashboard.jinax.render_response("admin/list.html", context)

    def _can_action(self, action_name: str) -> bool:
        user = getattr(self.request, "user", None)
        if user is None:
            return False
        try:
            self.dashboard.auth.authorize(
                user,
                self.dashboard.permission_for_action(self.admin_model.get_name(), action_name),
            )
            return True
        except Exception:
            try:
                self.dashboard.auth.authorize(user, "admin:superuser")
                return True
            except Exception:
                return False


class DetailView(AdminView):
    def __init__(self, admin_model: Any, request: Request, dashboard: Any, object_id: str) -> None:
        super().__init__(admin_model, request, dashboard)
        self.object_id = object_id

    async def render(self) -> HTMLResponse:
        model_class = self.admin_model.model
        obj = None
        if hasattr(model_class, "get_instance"):
            result = model_class.get_instance(self.object_id)
            obj = await result if hasattr(result, "__await__") else result

        context = {
            "model": self.admin_model,
            "models": self.dashboard.registry.get_all(),
            "object": obj,
            "verbose_name": self.admin_model.get_verbose_name(),
            "object_id": self.object_id,
            "fields": self.admin_model.fields,
            "user": getattr(self.request, "user", None),
            "can_change": self.dashboard.can_access_model(getattr(self.request, "user", None), self.admin_model.get_name(), "update"),
            "can_delete": self.dashboard.can_access_model(getattr(self.request, "user", None), self.admin_model.get_name(), "delete"),
        }
        return await self.dashboard.jinax.render_response("admin/detail.html", context)


class CreateView(AdminView):
    async def render(self) -> HTMLResponse | RedirectResponse:
        if self.request.method == "POST":
            # Extract form payload for model creation logic
            form_data = await self.request.form() if hasattr(self.request, "form") else {}
            form_data = self._form_dict(form_data)
            form_data = self.dashboard.validate_csrf(form_data)

            # Hook for model saving instance if supported by model manager
            model_class = self.admin_model.model
            result = None
            if hasattr(model_class, "create_instance"):
                result = model_class.create_instance(form_data)
                if hasattr(result, "__await__"):
                    await result
            record_id = str(result.get("id", "")) if isinstance(result, dict) else None
            self.dashboard.record_activity("created", self.admin_model.get_name(), self.request, record_id)

            return RedirectResponse(
                f"{self.dashboard.url_prefix}/{self.admin_model.get_name()}",
                status_code=302,
            )

        context = {
            "model": self.admin_model,
            "models": self.dashboard.registry.get_all(),
            "verbose_name": self.admin_model.get_verbose_name(),
            "fields": self.admin_model.fields,
            "readonly_fields": self.admin_model.readonly_fields,
            "version": "",
            "user": getattr(self.request, "user", None),
        }
        return await self.dashboard.jinax.render_response("admin/add.html", context)


class UpdateView(AdminView):
    def __init__(self, admin_model: Any, request: Request, dashboard: Any, object_id: str) -> None:
        super().__init__(admin_model, request, dashboard)
        self.object_id = object_id

    @staticmethod
    def _value(obj: Any, field: str) -> Any:
        if isinstance(obj, dict):
            value = obj.get(field, "")
        else:
            value = getattr(obj, field, "")
        return value() if callable(value) else value

    @staticmethod
    def _snapshot(obj: Any) -> dict[str, Any]:
        """Create a JSON-safe audit snapshot for adapters and custom models."""

        if obj is None:
            return {}
        if isinstance(obj, dict):
            value: Any = dict(obj)
        elif hasattr(obj, "to_dict"):
            value = obj.to_dict()
        else:
            value = dict(getattr(obj, "__dict__", {}))
        try:
            return json.loads(json.dumps(value, default=str))
        except (TypeError, ValueError):
            return {"value": str(value)}

    async def _get_object(self) -> Any:
        model_class = self.admin_model.model
        if not hasattr(model_class, "get_instance"):
            return None
        result = model_class.get_instance(self.object_id)
        return await result if hasattr(result, "__await__") else result

    async def render(self) -> HTMLResponse | RedirectResponse:
        model_class = self.admin_model.model

        if self.request.method == "POST":
            form_data = await self.request.form() if hasattr(self.request, "form") else {}
            form_data = self._form_dict(form_data)
            form_data = self.dashboard.validate_csrf(form_data)

            # FormData preserves repeated values. Use the final value so a
            # hidden false fallback plus a checked boolean is submitted safely.
            form_data = {
                key: value[-1] if isinstance(value, list) and value else value
                for key, value in form_data.items()
            }

            expected_version = form_data.pop("_version", None)
            save_mode = str(form_data.pop("_save", "list"))
            readonly_fields = set(self.admin_model.readonly_fields) | {"id"}
            form_data = {key: value for key, value in form_data.items() if key not in readonly_fields}
            current = await self._get_object()
            if expected_version not in (None, ""):
                current_version = current.get("updated_at") if isinstance(current, dict) else getattr(current, "updated_at", None) if current is not None else None
                if str(expected_version) != str(current_version):
                    raise Conflict("This record was changed by another user. Reload before saving.")

            before = self._snapshot(current)
            result = None
            if hasattr(model_class, "update_instance"):
                result = model_class.update_instance(self.object_id, form_data)
                if hasattr(result, "__await__"):
                    result = await result
            after = self._snapshot(result if result is not None else await self._get_object())
            details = {"before": before, "after": after} if before or after else {}
            self.dashboard.record_activity(
                "updated",
                self.admin_model.get_name(),
                self.request,
                self.object_id,
                **details,
            )

            if save_mode == "continue":
                target = f"{self.dashboard.url_prefix}/{self.admin_model.get_name()}/{self.object_id}/edit"
            elif save_mode == "add":
                target = f"{self.dashboard.url_prefix}/{self.admin_model.get_name()}/add"
            else:
                target = f"{self.dashboard.url_prefix}/{self.admin_model.get_name()}"
            return RedirectResponse(
                target,
                status_code=302,
            )

        obj = await self._get_object()
        field_values: dict[str, str] = {}
        field_raw_values: dict[str, Any] = {}
        for field in self.admin_model.fields:
            value = self._value(obj, field) if obj is not None else (self.object_id if field == "id" else "")
            field_raw_values[field] = value
            if value is None:
                field_values[field] = ""
            elif isinstance(value, (dict, list, tuple)):
                field_values[field] = json.dumps(value, indent=2, ensure_ascii=True, default=str)
            else:
                field_values[field] = str(value)

        entries = [
            item.to_dict()
            for item in self.dashboard.activities
            if item.resource == self.admin_model.get_name() and item.record_id == self.object_id
        ][::-1]
        label_field = next(
            (field for field in ("name", "title", "label", "slug") if field_values.get(field)),
            None,
        )
        record_label = field_values.get(label_field, self.object_id) if label_field else self.object_id
        last_modified = field_values.get("updated_at") or field_values.get("created_at") or ""

        context = {
            "model": self.admin_model,
            "models": self.dashboard.registry.get_all(),
            "object": obj,
            "verbose_name": self.admin_model.get_verbose_name(),
            "object_id": self.object_id,
            "fields": self.admin_model.fields,
            "verbose_name_plural": self.admin_model.get_verbose_name_plural(),
            "readonly_fields": self.admin_model.readonly_fields,
            "version": (obj.get("updated_at") if isinstance(obj, dict) else getattr(obj, "updated_at", "")) if obj is not None else "",
            "user": getattr(self.request, "user", None),
            "can_delete": self.dashboard.can_access_model(getattr(self.request, "user", None), self.admin_model.get_name(), "delete"),
            "field_values": field_values,
            "field_raw_values": field_raw_values,
            "history_entries": entries,
            "history_count": len(entries),
            "record_label": record_label,
            "last_modified": last_modified,
        }
        return await self.dashboard.jinax.render_response("admin/edit.html", context)


class DeleteView(AdminView):
    def __init__(self, admin_model: Any, request: Request, dashboard: Any, object_id: str) -> None:
        super().__init__(admin_model, request, dashboard)
        self.object_id = object_id

    async def render(self) -> HTMLResponse | RedirectResponse:
        if self.request.method == "POST":
            form_data = await self.request.form()
            self.dashboard.validate_csrf(self._form_dict(form_data))
            # Hook for deleting model instance
            model_class = self.admin_model.model
            if hasattr(model_class, "delete_instance"):
                result = model_class.delete_instance(self.object_id)
                if hasattr(result, "__await__"):
                    await result
            self.dashboard.record_activity("deleted", self.admin_model.get_name(), self.request, self.object_id)

            return RedirectResponse(
                f"{self.dashboard.url_prefix}/{self.admin_model.get_name()}",
                status_code=302,
            )

        obj = None
        model_class = self.admin_model.model
        if hasattr(model_class, "get_instance"):
            result = model_class.get_instance(self.object_id)
            obj = await result if hasattr(result, "__await__") else result

        context = {
            "model": self.admin_model,
            "models": self.dashboard.registry.get_all(),
            "verbose_name": self.admin_model.get_verbose_name(),
            "object_id": self.object_id,
            "object": obj,
            "fields": self.admin_model.fields,
            "user": getattr(self.request, "user", None),
        }
        return await self.dashboard.jinax.render_response("admin/delete.html", context)
