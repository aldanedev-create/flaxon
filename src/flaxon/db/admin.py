"""Adapt explicitly registered Tortoise models to Flaxon's Admin CRUD contract."""
from __future__ import annotations

import importlib
import json
from typing import Any
from tortoise import fields
from tortoise.fields.relational import BackwardFKRelation, BackwardOneToOneRelation, ManyToManyFieldInstance, ForeignKeyFieldInstance
from tortoise.exceptions import IntegrityError, ValidationError
from tortoise.expressions import Q
from tortoise.models import Model
from flaxon.exceptions import BadRequest, Conflict, NotFound
from .integration import optional_module


def model_adapter(model: type[Model], options: dict[str, Any]):
    columns = {}
    readonly = set(options.get("readonly_fields") or [])
    for name, field in model._meta.fields_map.items():
        if isinstance(field, (BackwardFKRelation, BackwardOneToOneRelation, ManyToManyFieldInstance)):
            continue
        if isinstance(field, ForeignKeyFieldInstance):
            columns[field.source_field or f"{name}_id"] = field
        else:
            columns[name] = field
        if field.pk or getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
            readonly.add(name)
    visible = options.setdefault("fields", list(columns))
    writable = set(visible) & set(columns) - readonly
    options["readonly_fields"] = sorted(readonly)
    options.setdefault("list_display", [model._meta.pk_attr or "id", *[n for n in columns if n not in readonly][:2]])
    search = options.get("search_fields") or []
    filters = options.get("list_filter") or []
    for name in [*search, *filters, *(options.get("ordering") or [])]:
        if name.lstrip("-") not in columns:
            raise ValueError(f"Unknown Admin field {name!r} on {model.__name__}")

    def payload(data):
        unknown = set(data) - set(columns)
        if unknown:
            raise BadRequest(f"Unknown model fields: {', '.join(sorted(unknown))}")
        result = {}
        for name, value in data.items():
            if name not in writable:
                continue
            if isinstance(value, list):
                value = value[-1] if value else ""
            field = columns[name]
            try:
                if value == "" and field.null:
                    result[name] = None
                    continue
                if isinstance(field, ForeignKeyFieldInstance):
                    target = field.related_model._meta.pk
                    value = target.to_python_value(value)
                elif isinstance(field, fields.BooleanField):
                    if isinstance(value, str):
                        if value.lower() not in {"true", "false", "1", "0", "on", "off"}:
                            raise ValueError("Expected a boolean")
                        value = value.lower() in {"true", "1", "on"}
                elif isinstance(field, fields.JSONField) and isinstance(value, str):
                    value = json.loads(value)
                else:
                    value = field.to_python_value(value)
                field.validate(value)
                result[name] = value
            except (ValueError, TypeError, ValidationError) as exc:
                raise BadRequest(f"Invalid value for {name}") from exc
        return result

    class Adapter:
        orm_model = model
        field_metadata = columns
        __name__ = model.__name__

        @classmethod
        async def form_schema(cls):
            schema = {}
            for name, field in columns.items():
                kind = "text"
                choices = None
                if isinstance(field, ForeignKeyFieldInstance):
                    kind = "number"
                    related = field.related_model
                    rows = await related.all().limit(101)
                    if len(rows) <= 100:
                        kind = "select"
                        choices = [(str(row.pk), str(row)) for row in rows]
                elif isinstance(field, fields.BooleanField):
                    kind = "checkbox"
                elif isinstance(field, fields.JSONField):
                    kind = "textarea"
                elif isinstance(field, fields.TextField):
                    kind = "textarea"
                elif isinstance(field, fields.DatetimeField):
                    kind = "datetime-local"
                elif isinstance(field, fields.DateField):
                    kind = "date"
                elif isinstance(field, (fields.IntField, fields.FloatField, fields.DecimalField)):
                    kind = "number"
                default = field.default() if callable(field.default) else field.default
                schema[name] = {
                    "kind": kind, "choices": choices, "default": default,
                    "required": not field.null and field.default is None and name not in readonly,
                    "max_length": getattr(field, "max_length", None),
                }
            return schema

        @classmethod
        async def query(cls, q=None, page=1, per_page=25, query_params=None):
            query = model.all()
            params = query_params or {}
            if q and search:
                conditions = Q()
                for name in search:
                    conditions |= Q(**{f"{name}__icontains": q})
                query = query.filter(conditions)
            for name in filters:
                value = params.get(f"filter_{name}")
                if value not in (None, ""):
                    query = query.filter(**{name: value})
            ordering = params.get("order_by")
            if ordering:
                if ordering.lstrip("-") not in columns:
                    raise BadRequest("Invalid ordering field")
                query = query.order_by(ordering)
            elif options.get("ordering"):
                query = query.order_by(*options["ordering"])
            total = await query.count()
            items = await query.offset((page - 1) * per_page).limit(per_page)
            return {"items": items, "total": total, "pages": max(1, (total + per_page - 1) // per_page), "page": page, "per_page": per_page}

        @classmethod
        async def get_instance(cls, object_id):
            try:
                obj = await model.get_or_none(pk=object_id)
            except (ValueError, TypeError) as exc:
                raise NotFound("Record not found") from exc
            if obj is None:
                raise NotFound("Record not found")
            return obj

        @classmethod
        async def create_instance(cls, data):
            try:
                return await model.create(**payload(data))
            except IntegrityError as exc:
                raise Conflict("A unique value already exists or a related record is invalid") from exc
            except (ValidationError, ValueError, TypeError) as exc:
                raise BadRequest("Invalid model data; check required fields and values") from exc

        @classmethod
        async def update_instance(cls, object_id, data):
            obj = await cls.get_instance(object_id)
            values = payload(data)
            try:
                obj.update_from_dict(values)
                await obj.save()
            except IntegrityError as exc:
                raise Conflict("A unique value already exists or a related record is invalid") from exc
            except (ValidationError, ValueError, TypeError) as exc:
                raise BadRequest("Invalid model data") from exc
            return obj

        @classmethod
        async def delete_instance(cls, object_id):
            obj = await cls.get_instance(object_id)
            try:
                await obj.delete()
            except IntegrityError as exc:
                raise Conflict("This record is referenced by another record") from exc

        @classmethod
        async def get_instances(cls):
            return await model.all()

        @classmethod
        async def count(cls):
            return await model.all().count()

    Adapter.__name__ = model.__name__
    return Adapter


def register_project_models(app, registry):
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
    from flaxon.admin import AdminConfig, AdminDashboard
    from flaxon.admin.registry import Registry
    from flaxon.management import admin_store
    settings = app.settings
    if not settings.ADMIN_ENABLED:
        return None
    registry = Registry()
    register_project_models(app, registry)
    store = admin_store(settings)
    dashboard = AdminDashboard(
        app, config=AdminConfig(site_title=f"{settings.PROJECT_NAME} admin", timezone=settings.TIME_ZONE),
        registry=registry, store=store, users=[], strict_permissions=True,
        upload_dir=str(settings.root / "data/uploads"),
        microservices=settings.ADMIN_SERVICES_ENABLED, session_bound_csrf=True,
    )
    # ORM is used by registered models. The existing Admin metadata store remains
    # separate; don't treat Database (the ORM lifecycle) as a raw SQL adapter.
    dashboard.database = None
    if settings.CMS_ENABLED:
        from flaxon.admin.cms import CMS, ContentType, CMSField
        cms = CMS(app, auth=dashboard.auth)
        cms.database = None
        cms.register(ContentType("page", label="Page", label_plural="Pages", fields=[CMSField("title", required=True), CMSField("body", type="richtext")]))
        app.cms = cms
    return dashboard
