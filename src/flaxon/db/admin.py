"""Adapt explicitly registered Tortoise models to Flaxon's Admin CRUD contract."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from tortoise import fields
from tortoise.exceptions import IntegrityError, ValidationError
from tortoise.expressions import Q
from tortoise.fields.relational import (
    BackwardFKRelation,
    BackwardOneToOneRelation,
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
)
from tortoise.models import Model
from tortoise.transactions import in_transaction

from flaxon._imports import import_attribute
from flaxon.exceptions import BadRequest, Conflict, Forbidden, NotFound

from .integration import optional_module

admin_context = ContextVar("flaxon_admin_context", default=None)


class _TortoiseAdminAdapter:
    """Implement Admin operations using per-model adapter configuration."""

    @classmethod
    def _payload(cls, data):
        unknown = (
            set(data)
            - set(cls._columns)
            - set(cls._relations)
            - {f"_inline_{name}" for name in cls._options.get("inlines", {})}
        )
        if unknown:
            raise BadRequest(f"Unknown model fields: {', '.join(sorted(unknown))}")
        result = {}
        for name, raw_value in data.items():
            value = raw_value
            if name not in cls._writable:
                continue
            if isinstance(value, list):
                value = value[-1] if value else ""
            field = cls._columns[name]
            try:
                if value == "" and field.null:
                    result[name] = None
                    continue
                if isinstance(field, ForeignKeyFieldInstance):
                    target = field.related_model._meta.pk
                    value = target.to_python_value(value)
                elif isinstance(field, fields.BooleanField):
                    value = cls._boolean_value(value)
                elif isinstance(field, fields.JSONField) and isinstance(value, str):
                    value = json.loads(value)
                else:
                    value = field.to_python_value(value)
                field.validate(value)
                result[name] = value
            except (ValueError, TypeError, ValidationError) as exc:
                error = BadRequest(f"Invalid value for {name}")
                error.field_errors = {name: "Enter a valid value."}
                raise error from exc
        return result

    @staticmethod
    def _boolean_value(value):
        if not isinstance(value, str):
            return value
        if value.lower() not in {"true", "false", "1", "0", "on", "off"}:
            raise ValueError("Expected a boolean")
        return value.lower() in {"true", "1", "on"}

    @classmethod
    def transaction(cls):
        return in_transaction()

    @classmethod
    async def version(cls, obj):
        values = {name: getattr(obj, name, None) for name in cls._model._meta.fields_db_projection}
        for name in cls._relations:
            values[name] = sorted(str(row.pk) for row in await getattr(obj, name).all())
        return hashlib.sha256(json.dumps(values, sort_keys=True, default=str).encode()).hexdigest()

    @classmethod
    async def authorize(cls, action, target):
        context = admin_context.get()
        if context is None:
            return
        dashboard, user = context
        registered = cls.registry.get_by_model(cls._model)
        if registered is None:
            raise Forbidden("Model is not registered")
        await dashboard.auth.authorize_async(
            user, dashboard.permission_for_action(registered.get_name(), action)
        )
        evaluate_permission_hook = import_attribute("flaxon.admin.registry", "evaluate_permission_hook")
        if not await evaluate_permission_hook(registered.get_permission_hook(action), user, target):
            raise Forbidden("This record operation is not permitted")

    @classmethod
    async def visible_query(cls):
        query = cls._model.all()
        context = admin_context.get()
        hook = cls._options.get("queryset")
        if hook and context:
            query = hook(context[1], query)
            query_set_type = import_attribute("tortoise.queryset", "QuerySet")
            if not isinstance(query, query_set_type) and hasattr(query, "__await__"):
                query = await query
        return query

    @classmethod
    async def related_rows(cls, field, needle=""):
        context = admin_context.get()
        if not context or cls.registry is None:
            raise Forbidden("Relationship selection requires an authenticated Admin request")
        dashboard, user = context
        registered = cls.registry.get_by_model(field.related_model)
        if registered is None:
            raise Forbidden("Register related models to select their records")
        await dashboard.auth.authorize_async(
            user, dashboard.permission_for_action(registered.get_name(), "read")
        )
        query = await registered.model.visible_query()
        if needle and registered.search_fields:
            conditions = Q()
            for name in registered.search_fields:
                conditions |= Q(**{f"{name}__icontains": needle})
            query = query.filter(conditions)
        evaluate_permission_hook = import_attribute("flaxon.admin.registry", "evaluate_permission_hook")
        return (
            [
                row
                async for row in query
                if await evaluate_permission_hook(registered.get_permission_hook("read"), user, row)
            ]
            if registered.get_permission_hook("read")
            else await query
        )

    @classmethod
    async def validate_relations(cls, data):
        for name, field in {**cls._columns, **cls._relations}.items():
            if not isinstance(field, (ForeignKeyFieldInstance, ManyToManyFieldInstance)) or name not in data:
                continue
            values = data[name]
            if isinstance(field, ManyToManyFieldInstance):
                if isinstance(values, str):
                    try:
                        values = json.loads(values or "[]")
                    except ValueError as exc:
                        raise BadRequest("Relationship IDs must be a JSON list") from exc
                if not isinstance(values, list) or len(values) > 200:
                    raise BadRequest("Select at most 200 related records")
            else:
                values = [values[-1] if isinstance(values, list) else values]
            selected = {str(value) for value in values if value not in (None, "")}
            allowed = {str(row.pk) for row in await cls.related_rows(field)}
            if not selected <= allowed:
                raise Forbidden("A selected relationship is unavailable")

    @classmethod
    async def save_relations(cls, obj, data):
        for name, field in cls._relations.items():
            if name in data:
                values = json.loads(data[name] or "[]") if isinstance(data[name], str) else data[name]
                rows = await field.related_model.filter(pk__in=values)
                await getattr(obj, name).clear()
                if rows:
                    await getattr(obj, name).add(*rows)

    @classmethod
    async def inline_schema(cls, obj=None):
        schema = {}
        context = admin_context.get()
        if not context:
            return schema
        dashboard, user = context
        for name, config in cls._options.get("inlines", {}).items():
            registered = cls.registry.get_by_model(config["model"])
            if not registered:
                raise ValueError("Inline models must be registered")
            await dashboard.auth.authorize_async(
                user, dashboard.permission_for_action(registered.get_name(), "read")
            )
            adapter = registered.model
            fields_to_show = [
                field
                for field in registered.fields
                if field not in registered.readonly_fields and field != config["fk"]
            ]
            rows = []
            if obj:
                query = await adapter.visible_query()
                evaluate_permission_hook = import_attribute(
                    "flaxon.admin.registry", "evaluate_permission_hook"
                )
                for row in await query.filter(**{config["fk"]: obj.pk}).limit(101):
                    if await evaluate_permission_hook(registered.get_permission_hook("read"), user, row):
                        rows.append({
                            "id": str(row.pk),
                            "_version": await adapter.version(row),
                            **{field: getattr(row, field, None) for field in fields_to_show},
                        })
                if len(rows) > 100:
                    raise BadRequest("Use the child model list to edit more than 100 records")
            schema[name] = {"fields": fields_to_show, "rows": json.dumps(rows, default=str)}
        return schema

    @classmethod
    async def save_inlines(cls, obj, data):
        context = admin_context.get()
        for name, config in cls._options.get("inlines", {}).items():
            key = f"_inline_{name}"
            if key not in data:
                continue
            try:
                rows = json.loads(data[key]) if isinstance(data[key], str) else data[key]
            except ValueError as exc:
                raise BadRequest("Invalid child records") from exc
            if not isinstance(rows, list) or len(rows) > 100:
                raise BadRequest("At most 100 child records can be edited together")
            if not context:
                raise Forbidden("Inline editing requires Admin authentication")
            dashboard, user = context
            registered = cls.registry.get_by_model(config["model"])
            if not registered:
                raise Forbidden("Register the inline model")
            for raw in rows:
                await cls._save_inline_row(
                    obj, raw, config=config, registered=registered, dashboard=dashboard, user=user
                )

    @classmethod
    async def _save_inline_row(cls, obj, raw, *, config, registered, dashboard, user):
        adapter = registered.model
        evaluate_permission_hook = import_attribute("flaxon.admin.registry", "evaluate_permission_hook")
        if not isinstance(raw, dict):
            raise BadRequest("Invalid child record")
        values = dict(raw)
        identifier = values.pop("id", None)
        deleting = values.pop("_delete", False)
        expected = values.pop("_version", None)
        child = await adapter.get_instance(identifier) if identifier else None
        if child and str(getattr(child, config["fk"])) != str(obj.pk):
            raise Forbidden("Child record belongs to another parent")
        action = "delete" if deleting else "update" if child else "create"
        await dashboard.auth.authorize_async(
            user, dashboard.permission_for_action(registered.get_name(), action)
        )
        if not await evaluate_permission_hook(registered.get_permission_hook(action), user, child or values):
            raise Forbidden("Child operation is not permitted")
        if deleting:
            if child:
                await adapter.delete_instance(identifier)
        else:
            values[config["fk"]] = obj.pk
            if child:
                await adapter.update_instance(identifier, values, expected_version=expected)
            else:
                await adapter.create_instance(values)

    @classmethod
    async def form_schema(cls):
        schema = {}
        for name, field in cls._columns.items():
            kind = "text"
            choices = None
            if isinstance(field, ForeignKeyFieldInstance):
                kind = "number"
                rows = await cls.related_rows(field)
                if len(rows) <= 100:
                    kind = "select"
                    choices = [(str(row.pk), str(row)) for row in rows]
                else:
                    kind = "autocomplete"
            elif isinstance(field, fields.BooleanField):
                kind = "checkbox"
            elif isinstance(field, (fields.JSONField, fields.TextField)):
                kind = "textarea"
            elif isinstance(field, fields.DatetimeField):
                kind = "datetime-local"
            elif isinstance(field, fields.DateField):
                kind = "date"
            elif isinstance(field, (fields.IntField, fields.FloatField, fields.DecimalField)):
                kind = "number"
            default = field.default() if callable(field.default) else field.default
            schema[name] = {
                "kind": kind,
                "choices": choices,
                "default": default,
                "required": not field.null and field.default is None and (name not in cls._readonly),
                "max_length": getattr(field, "max_length", None),
                "widget": (cls._options.get("widgets") or {}).get(name),
            }
        for name in cls._relations:
            rows = await cls.related_rows(cls._relations[name])
            schema[name] = {
                "kind": "autocomplete-many" if len(rows) > 100 else "many",
                "required": False,
                "default": "[]",
                "choices": [(str(row.pk), str(row)) for row in rows[:100]],
            }
        return schema

    @classmethod
    async def query(cls, q=None, page=1, per_page=25, query_params=None):
        query = await cls.visible_query()
        params = query_params or {}
        if q and cls._search:
            conditions = Q()
            for name in cls._search:
                conditions |= Q(**{f"{name}__icontains": q})
            query = query.filter(conditions)
        for name in cls._filters:
            value = params.get(f"filter_{name}")
            if value not in (None, ""):
                query = query.filter(**{name: value})
        ordering = params.get("order_by")
        if ordering:
            if ordering.lstrip("-") not in cls._columns:
                raise BadRequest("Invalid ordering field")
            query = query.order_by(ordering)
        elif cls._options.get("ordering"):
            query = query.order_by(*cls._options["ordering"])
        else:
            query = query.order_by(cls._model._meta.pk_attr)
        context = admin_context.get()
        read_hook = cls._options.get("can_view")
        if read_hook and context:
            evaluate_permission_hook = import_attribute("flaxon.admin.registry", "evaluate_permission_hook")
            visible = [
                row async for row in query if await evaluate_permission_hook(read_hook, context[1], row)
            ]
            total = len(visible)
            items = visible[(page - 1) * per_page : page * per_page]
            return {
                "items": items,
                "total": total,
                "pages": max(1, (total + per_page - 1) // per_page),
                "page": page,
                "per_page": per_page,
            }
        total = await query.count()
        items = await query.offset((page - 1) * per_page).limit(per_page)
        return {
            "items": items,
            "total": total,
            "pages": max(1, (total + per_page - 1) // per_page),
            "page": page,
            "per_page": per_page,
        }

    @classmethod
    async def get_instance(cls, object_id):
        try:
            query = await cls.visible_query()
            obj = await query.get_or_none(pk=object_id)
        except (ValueError, TypeError) as exc:
            raise NotFound("Record not found") from exc
        if obj is None:
            raise NotFound("Record not found")
        return obj

    @classmethod
    async def create_instance(cls, data):
        await cls.authorize("create", data)
        try:
            missing = {
                name: "This field is required."
                for name, field in cls._columns.items()
                if name in cls._writable
                and (not field.null)
                and (field.default is None)
                and (not getattr(field, "generated", False))
                and (name not in data)
            }
            if missing:
                error = BadRequest("Complete the required fields.")
                error.field_errors = missing
                raise error
            await cls.validate_relations(data)
            async with in_transaction():
                obj = await cls._model.create(**cls._payload(data))
                await cls.save_relations(obj, data)
                await cls.save_inlines(obj, data)
                return obj
        except IntegrityError as exc:
            raise Conflict("A unique value already exists or a related record is invalid") from exc
        except (ValidationError, ValueError, TypeError) as exc:
            raise BadRequest("Invalid model data; check required fields and values") from exc

    @classmethod
    async def update_instance(cls, object_id, data, expected_version=None):
        obj = await cls.get_instance(object_id)
        await cls.authorize("update", obj)
        values = cls._payload(data)
        await cls.validate_relations(data)
        try:
            async with in_transaction():
                obj = await cls._model.select_for_update().get(pk=object_id)
                if expected_version and await cls.version(obj) != expected_version:
                    raise Conflict("This record changed. Reload before saving.")
                for name, field in cls._columns.items():
                    if getattr(field, "auto_now", False):
                        values[name] = datetime.now(UTC)
                original = {name: getattr(obj, name) for name in cls._model._meta.fields_db_projection}
                obj.update_from_dict(values)
                changed = (
                    await cls._model.filter(
                        pk=object_id,
                        **{
                            name: value
                            for name, value in original.items()
                            if name != cls._model._meta.pk_attr
                        },
                    ).update(**values)
                    if values
                    else 1
                )
                if not changed:
                    raise Conflict("This record changed. Reload before saving.")
                await cls.save_relations(obj, data)
                await cls.save_inlines(obj, data)
        except IntegrityError as exc:
            raise Conflict("A unique value already exists or a related record is invalid") from exc
        except (ValidationError, ValueError, TypeError) as exc:
            raise BadRequest("Invalid model data") from exc
        return obj

    @classmethod
    async def deletion_preview(cls, object_id):
        obj = await cls.get_instance(object_id)
        dependencies = []
        for name, field in cls._model._meta.fields_map.items():
            if isinstance(field, (BackwardFKRelation, BackwardOneToOneRelation)):
                count = await field.related_model.filter(**{field.relation_field: obj.pk}).count()
                if count:
                    dependencies.append({
                        "relation": name,
                        "count": count,
                        "behavior": str(
                            next(
                                (
                                    relation.on_delete
                                    for relation in field.related_model._meta.fields_map.values()
                                    if isinstance(relation, ForeignKeyFieldInstance)
                                    and relation.source_field == field.relation_field
                                ),
                                "DATABASE",
                            )
                        ),
                    })
        return dependencies

    @classmethod
    async def authorize_cascade(cls, obj, visited=None):
        visited = visited if visited is not None else set()
        identity = (type(obj), str(obj.pk))
        if identity in visited:
            return
        visited.add(identity)
        context = admin_context.get()
        for field in obj._meta.fields_map.values():
            if not isinstance(field, (BackwardFKRelation, BackwardOneToOneRelation)):
                continue
            forward = next(
                (
                    relation
                    for relation in field.related_model._meta.fields_map.values()
                    if isinstance(relation, ForeignKeyFieldInstance)
                    and relation.source_field == field.relation_field
                ),
                None,
            )
            if forward is None or str(forward.on_delete) != "CASCADE":
                continue
            children = field.related_model.filter(**{field.relation_field: obj.pk})
            if not await children.exists():
                continue
            if not context:
                raise Forbidden("Cascade deletion requires authenticated Admin permissions")
            dashboard, user = context
            registered = cls.registry.get_by_model(field.related_model)
            if registered is None:
                raise Forbidden("Register dependent models before cascading deletion")
            await dashboard.auth.authorize_async(
                user, dashboard.permission_for_action(registered.get_name(), "delete")
            )
            evaluate_permission_hook = import_attribute("flaxon.admin.registry", "evaluate_permission_hook")
            async for child in children:
                if not await evaluate_permission_hook(registered.get_permission_hook("delete"), user, child):
                    raise Forbidden("Deletion of a dependent record is not permitted")
                await cls.authorize_cascade(child, visited)

    @classmethod
    async def delete_instance(cls, object_id):
        obj = await cls.get_instance(object_id)
        await cls.authorize("delete", obj)
        try:
            async with in_transaction():
                obj = await cls._model.select_for_update().get(pk=object_id)
                await cls.authorize_cascade(obj)
                await obj.delete()
        except IntegrityError as exc:
            raise Conflict("This record is referenced by another record") from exc

    @classmethod
    async def get_instances(cls):
        return await (await cls.visible_query())

    @classmethod
    async def count(cls):
        return await (await cls.visible_query()).count()


def model_adapter(model: type[Model], options: dict[str, Any]):
    """Perform the model adapter operation for this subsystem."""
    columns = {}
    relations = {}
    readonly = set(options.get("readonly_fields") or [])
    for name, field in model._meta.fields_map.items():
        if isinstance(field, ManyToManyFieldInstance):
            relations[name] = field
            continue
        if isinstance(field, (BackwardFKRelation, BackwardOneToOneRelation)):
            continue
        if isinstance(field, ForeignKeyFieldInstance):
            columns[field.source_field or f"{name}_id"] = field
        elif name not in columns:
            columns[name] = field
        if field.pk or getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
            readonly.add(name)
    visible = options.setdefault("fields", list(columns) + list(relations))
    writable = set(visible) & set(columns) - readonly
    options["readonly_fields"] = sorted(readonly)
    options.setdefault(
        "list_display", [model._meta.pk_attr or "id", *[n for n in columns if n not in readonly][:2]]
    )
    search = options.get("search_fields") or []
    filters = options.get("list_filter") or []
    for name in [*search, *filters, *(options.get("ordering") or [])]:
        if name.lstrip("-") not in columns:
            raise ValueError(f"Unknown Admin field {name!r} on {model.__name__}")

    return type(
        model.__name__,
        (_TortoiseAdminAdapter,),
        {
            "orm_model": model,
            "field_metadata": columns,
            "admin_options": options,
            "registry": None,
            "_model": model,
            "_columns": columns,
            "_relations": relations,
            "_readonly": readonly,
            "_writable": writable,
            "_options": options,
            "_search": search,
            "_filters": filters,
            "relationship_fields": {
                **{
                    name: field
                    for name, field in columns.items()
                    if isinstance(field, ForeignKeyFieldInstance)
                },
                **relations,
            },
        },
    )


def register_project_models(app, registry):
    """Register the project models."""
    modules = ["admin"] if optional_module("admin") else []
    for module in getattr(app, "_orm_modules", []):
        path = module.admin_module
        if path is None and module.models_module:
            candidate = f"{module.models_module.rsplit('.', 1)[0]}.admin"
            path = candidate if optional_module(candidate) else None
        if path and path not in modules:
            modules.append(path)
    for name in modules:
        registrar = getattr(importlib.import_module(name), "register", None)
        if not callable(registrar):
            raise ValueError(f"{name} must define register(admin)")
        registrar(registry)


def configure_admin(app):
    """Configure durable staff Admin and CMS from the project's shared settings."""
    admin_config_type = import_attribute("flaxon.admin", "AdminConfig")
    admin_dashboard_type = import_attribute("flaxon.admin", "AdminDashboard")
    registry_type = import_attribute("flaxon.admin.registry", "Registry")
    admin_store = import_attribute("flaxon.management", "admin_store")

    settings = app.settings
    if not settings.ADMIN_ENABLED:
        return None
    registry = registry_type()
    register_project_models(app, registry)
    store = admin_store(settings)
    if hasattr(store, "close"):

        async def close_store():
            await asyncio.to_thread(store.close)

        app.on_shutdown(close_store)
    dashboard = admin_dashboard_type(
        app,
        config=admin_config_type(site_title=f"{settings.PROJECT_NAME} admin", timezone=settings.TIME_ZONE),
        registry=registry,
        store=store,
        users=[],
        strict_permissions=True,
        upload_dir=str(settings.root / "data/uploads"),
        microservices=settings.ADMIN_SERVICES_ENABLED,
        session_bound_csrf=True,
    )
    # ORM is used by registered models. The existing Admin metadata store remains
    # separate; don't treat Database (the ORM lifecycle) as a raw SQL adapter.
    dashboard.database = None
    if settings.CMS_ENABLED:
        cms_type = import_attribute("flaxon.admin.cms", "CMS")
        cmsfield_type = import_attribute("flaxon.admin.cms", "CMSField")
        content_type_type = import_attribute("flaxon.admin.cms", "ContentType")

        cms = cms_type(app, auth=dashboard.auth)
        cms.database = None
        cms.register(
            content_type_type(
                "page",
                label="Page",
                label_plural="Pages",
                fields=[cmsfield_type("title", required=True), cmsfield_type("body", type="richtext")],
            )
        )
        app.cms = cms
    return dashboard
