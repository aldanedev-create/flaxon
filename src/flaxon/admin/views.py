from __future__ import annotations

import json
from typing import Any

from flaxon._imports import import_attribute
from flaxon.exceptions import BadRequest, Conflict, Forbidden
from flaxon.http import HTMLResponse, RedirectResponse, Request

from .registry import evaluate_permission_hook


class AdminView:
    """Admin view implementation for the admin subsystem."""

    def __init__(self, admin_model: Any, request: Request, dashboard: Any) -> None:
        self.admin_model = admin_model
        self.request = request
        self.dashboard = dashboard

    async def invalid_form(self, error, data, template, obj=None):
        """Perform the invalid form operation for admin view."""
        adapter = self.admin_model.model
        schema = await adapter.form_schema() if hasattr(adapter, "form_schema") else {}
        context = {
            "model": self.admin_model,
            "models": self.dashboard.registry.get_all(),
            "verbose_name": self.admin_model.get_verbose_name(),
            "fields": self.admin_model.fields,
            "readonly_fields": self.admin_model.readonly_fields,
            "form_schema": schema,
            "field_values": data,
            "field_raw_values": data,
            "field_errors": getattr(error, "field_errors", {}),
            "form_error": str(error),
            "user": getattr(self.request, "user", None),
            "object": obj,
            "object_id": getattr(self, "object_id", ""),
            "version": await adapter.version(obj) if obj is not None and hasattr(adapter, "version") else "",
            "verbose_name_plural": self.admin_model.get_verbose_name_plural(),
            "record_label": str(getattr(obj, "pk", "")),
            "history_count": 0,
            "history_entries": [],
            "last_modified": "",
            "can_delete": False,
            "inline_schema": await adapter.inline_schema(obj) if hasattr(adapter, "inline_schema") else {},
        }
        for name, inline in context["inline_schema"].items():
            submitted = data.get(f"_inline_{name}")
            if isinstance(submitted, str):
                try:
                    rows = json.loads(submitted)
                    if isinstance(rows, list) and len(rows) <= 100:
                        inline["rows"] = json.dumps(rows)
                except ValueError:
                    pass
        return await self.dashboard.jinax.render_response(template, context, status_code=400)

    async def render(self) -> HTMLResponse | RedirectResponse:
        """Render the requested content using the supplied context."""
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
    """Change list view implementation for the admin subsystem."""

    def _filter_legacy_objects(self, objects):
        needle = self.request.query.get("q", "").lower()
        if needle:
            fields = self.admin_model.search_fields or self.admin_model.fields
            objects = [
                obj
                for obj in objects
                if any(
                    needle in str(obj.get(f) if isinstance(obj, dict) else getattr(obj, f, "")).lower()
                    for f in fields
                )
            ]
        for field in self.admin_model.list_filter:
            value = self.request.query.get(f"filter_{field}", "")
            if value:
                objects = [
                    obj
                    for obj in objects
                    if str(obj.get(field) if isinstance(obj, dict) else getattr(obj, field, "")) == value
                ]
        ordering = self.request.query.get("order_by")
        if ordering:
            reverse = ordering.startswith("-")
            key = ordering.lstrip("-")
            objects.sort(
                key=lambda obj: obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None),
                reverse=reverse,
            )
        return objects

    async def render(self) -> HTMLResponse:
        """Render the requested content using the supplied context."""
        model_class = self.admin_model.model
        objects: list[Any] = []
        try:
            page = max(1, int(self.request.query.get("page", "1") or 1))
            per_page = min(200, max(1, int(self.request.query.get("per_page", "25") or 25)))
        except (ValueError, TypeError) as exc:
            bad_request_type = import_attribute("flaxon.exceptions", "BadRequest")

            raise bad_request_type("page and per_page must be integers") from exc
        query_result = None
        if hasattr(model_class, "query"):
            query_options = {"q": self.request.query.get("q") or None, "page": page, "per_page": per_page}
            if hasattr(model_class, "orm_model"):
                query_options["query_params"] = self.request.query
            result = model_class.query(**query_options)
            query_result = await result if hasattr(result, "__await__") else result
            objects = list(query_result.get("items", []))
        elif hasattr(model_class, "get_instances"):
            result = model_class.get_instances()
            objects = list(await result if hasattr(result, "__await__") else result)
            objects = self._filter_legacy_objects(objects)
            total = len(objects)
            objects = objects[(page - 1) * per_page : page * per_page]
            query_result = {
                "total": total,
                "pages": max(1, (total + per_page - 1) // per_page),
                "page": page,
                "per_page": per_page,
            }

        # Object-level read rules are applied after the adapter query so
        # custom Admin models can keep their data source unchanged.
        hook = self.admin_model.get_permission_hook("read")
        if hook is not None and not hasattr(model_class, "orm_model"):
            visible = []
            for obj in objects:
                allowed = await evaluate_permission_hook(hook, getattr(self.request, "user", None), obj)
                if allowed:
                    visible.append(obj)
            objects = visible
            if query_result is not None:
                query_result = {
                    **query_result,
                    "total": len(visible),
                    "pages": page + int(len(objects) == per_page),
                }

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
                name: action
                for name, action in self.admin_model.get_actions().items()
                if self._can_action(name)
            },
            "user": getattr(self.request, "user", None),
            "request": self.request,
            "query": self.request.query.get("q", ""),
            "pagination": query_result
            or {"total": len(objects), "pages": 1, "page": 1, "per_page": len(objects)},
            "can_add": self.dashboard.can_access_model(
                getattr(self.request, "user", None), self.admin_model.get_name(), "create"
            ),
            "can_change": self.dashboard.can_access_model(
                getattr(self.request, "user", None), self.admin_model.get_name(), "update"
            ),
            "can_delete": self.dashboard.can_access_model(
                getattr(self.request, "user", None), self.admin_model.get_name(), "delete"
            ),
            "can_import": self.dashboard.can_access_model(
                getattr(self.request, "user", None), self.admin_model.get_name(), "create"
            ),
            "can_export": self.dashboard.can_access_model(
                getattr(self.request, "user", None), self.admin_model.get_name(), "read"
            ),
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
        except Forbidden:
            try:
                self.dashboard.auth.authorize(user, "admin:superuser")
                return True
            except Forbidden:
                return False


class DetailView(AdminView):
    """Detail view implementation for the admin subsystem."""

    def __init__(self, admin_model: Any, request: Request, dashboard: Any, object_id: str) -> None:
        super().__init__(admin_model, request, dashboard)
        self.object_id = object_id

    async def render(self) -> HTMLResponse:
        """Render the requested content using the supplied context."""
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
            "can_change": self.dashboard.can_access_model(
                getattr(self.request, "user", None), self.admin_model.get_name(), "update"
            ),
            "can_delete": self.dashboard.can_access_model(
                getattr(self.request, "user", None), self.admin_model.get_name(), "delete"
            ),
        }
        return await self.dashboard.jinax.render_response("admin/detail.html", context)


class CreateView(AdminView):
    """Create view implementation for the admin subsystem."""

    async def render(self) -> HTMLResponse | RedirectResponse:
        """Render the requested content using the supplied context."""
        if self.request.method == "POST":
            # Extract form payload for model creation logic
            form_data = await self.request.form() if hasattr(self.request, "form") else {}
            form_data = self._form_dict(form_data)
            form_data = self.dashboard.validate_csrf(form_data)

            form_data.pop("_save", None)
            readonly = set(self.admin_model.readonly_fields) | {"id"}
            form_data = {key: value for key, value in form_data.items() if key not in readonly}

            # Hook for model saving instance if supported by model manager
            model_class = self.admin_model.model
            result = None
            if hasattr(model_class, "create_instance"):
                try:
                    result = model_class.create_instance(form_data)
                    if hasattr(result, "__await__"):
                        result = await result
                except BadRequest as exc:
                    return await self.invalid_form(exc, form_data, "admin/add.html")
            record_id = (
                str(result.get("id", "")) if isinstance(result, dict) else str(getattr(result, "pk", ""))
            )
            self.dashboard.record_activity("created", self.admin_model.get_name(), self.request, record_id)

            return RedirectResponse(
                f"{self.dashboard.url_prefix}/{self.admin_model.get_name()}",
                status_code=302,
            )

        context = {
            "inline_schema": await self.admin_model.model.inline_schema(locals().get("obj"))
            if hasattr(self.admin_model.model, "inline_schema")
            else {},
            "form_schema": await self.admin_model.model.form_schema()
            if hasattr(self.admin_model.model, "form_schema")
            else {},
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
    """Update view implementation for the admin subsystem."""

    def __init__(self, admin_model: Any, request: Request, dashboard: Any, object_id: str) -> None:
        super().__init__(admin_model, request, dashboard)
        self.object_id = object_id

    @staticmethod
    def _value(obj: Any, field: str) -> Any:
        value = obj.get(field, "") if isinstance(obj, dict) else getattr(obj, field, "")
        return value() if callable(value) else value

    @staticmethod
    def _snapshot(obj: Any) -> dict[str, Any]:
        """Create a JSON-safe audit snapshot for adapters and custom models."""
        if obj is None:
            return {}
        if isinstance(obj, dict):
            value: Any = dict(obj)
        elif hasattr(obj, "_meta") and hasattr(obj._meta, "fields_db_projection"):
            value = {name: getattr(obj, name, None) for name in obj._meta.fields_db_projection}
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
        """Render the requested content using the supplied context."""
        model_class = self.admin_model.model

        if self.request.method == "POST":
            return await self._render_post(model_class=model_class)

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

        if hasattr(model_class, "relationship_fields"):
            many_to_many_field_instance_type = import_attribute(
                "tortoise.fields.relational", "ManyToManyFieldInstance"
            )

            for name, relation in model_class.relationship_fields.items():
                if isinstance(relation, many_to_many_field_instance_type):
                    field_values[name] = json.dumps([str(row.pk) for row in await getattr(obj, name).all()])
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
            "inline_schema": await self.admin_model.model.inline_schema(locals().get("obj"))
            if hasattr(self.admin_model.model, "inline_schema")
            else {},
            "form_schema": await self.admin_model.model.form_schema()
            if hasattr(self.admin_model.model, "form_schema")
            else {},
            "model": self.admin_model,
            "models": self.dashboard.registry.get_all(),
            "object": obj,
            "verbose_name": self.admin_model.get_verbose_name(),
            "object_id": self.object_id,
            "fields": self.admin_model.fields,
            "verbose_name_plural": self.admin_model.get_verbose_name_plural(),
            "readonly_fields": self.admin_model.readonly_fields,
            "version": await model_class.version(obj)
            if hasattr(model_class, "version")
            else (obj.get("updated_at") if isinstance(obj, dict) else getattr(obj, "updated_at", ""))
            if obj is not None
            else "",
            "user": getattr(self.request, "user", None),
            "can_delete": self.dashboard.can_access_model(
                getattr(self.request, "user", None), self.admin_model.get_name(), "delete"
            ),
            "field_values": field_values,
            "field_raw_values": field_raw_values,
            "history_entries": entries,
            "history_count": len(entries),
            "record_label": record_label,
            "last_modified": last_modified,
        }
        return await self.dashboard.jinax.render_response("admin/edit.html", context)

    async def _render_post(self, *, model_class):
        """Handle post behavior for render."""
        form_data = await self.request.form() if hasattr(self.request, "form") else {}
        form_data = self._form_dict(form_data)
        form_data = self.dashboard.validate_csrf(form_data)

        # FormData preserves repeated values. Use the final value so a
        # hidden false fallback plus a checked boolean is submitted safely.
        form_data = {
            key: value[-1] if isinstance(value, list) and value else value for key, value in form_data.items()
        }

        expected_version = form_data.pop("_version", None)
        if hasattr(model_class, "version") and not expected_version:
            raise BadRequest("Reload the edit form before saving; its record version is required")
        save_mode = str(form_data.pop("_save", "list"))
        readonly_fields = set(self.admin_model.readonly_fields) | {"id"}
        form_data = {key: value for key, value in form_data.items() if key not in readonly_fields}
        current = await self._get_object()
        if expected_version not in (None, "") and not hasattr(model_class, "version"):
            current_version = (
                current.get("updated_at")
                if isinstance(current, dict)
                else getattr(current, "updated_at", None)
                if current is not None
                else None
            )
            if str(expected_version) != str(current_version):
                raise Conflict("This record was changed by another user. Reload before saving.")

        before = self._snapshot(current)
        result = None
        if hasattr(model_class, "update_instance"):
            try:
                result = (
                    model_class.update_instance(self.object_id, form_data, expected_version=expected_version)
                    if hasattr(model_class, "version")
                    else model_class.update_instance(self.object_id, form_data)
                )
                if hasattr(result, "__await__"):
                    result = await result
            except BadRequest as exc:
                return await self.invalid_form(exc, form_data, "admin/edit.html", current)
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


class DeleteView(AdminView):
    """Delete view implementation for the admin subsystem."""

    def __init__(self, admin_model: Any, request: Request, dashboard: Any, object_id: str) -> None:
        super().__init__(admin_model, request, dashboard)
        self.object_id = object_id

    async def render(self) -> HTMLResponse | RedirectResponse:
        """Render the requested content using the supplied context."""
        if self.request.method == "POST":
            form_data = await self.request.form()
            self.dashboard.validate_csrf(self._form_dict(form_data))
            # Hook for deleting model instance
            model_class = self.admin_model.model
            if hasattr(model_class, "delete_instance"):
                result = model_class.delete_instance(self.object_id)
                if hasattr(result, "__await__"):
                    await result
            self.dashboard.record_activity(
                "deleted", self.admin_model.get_name(), self.request, self.object_id
            )

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
            "deletion_preview": await model_class.deletion_preview(self.object_id)
            if hasattr(model_class, "deletion_preview")
            else [],
            "fields": self.admin_model.fields,
            "user": getattr(self.request, "user", None),
        }
        return await self.dashboard.jinax.render_response("admin/delete.html", context)
