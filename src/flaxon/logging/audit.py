from __future__ import annotations

import logging
from typing import Any

from flaxon._imports import import_attribute
from flaxon.http import Request

from .formatters import AuditFormatter


class AuditLogger:
    """Record authentication and resource-management actions as audit events."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("flaxon.audit")
        self._configure()

    def _configure(self) -> None:
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = AuditFormatter()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

    def log(  # noqa: PLR0917 - preserve existing positional API
        self,
        action: str,
        user_id: str | int | None = None,
        resource: str | None = None,
        changes: dict[str, Any] | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        status: str = "success",
        error: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Write an audit action with its actor, resource, changes, and outcome."""
        log_data = {
            "action": action,
            "user_id": str(user_id) if user_id else None,
            "resource": resource,
            "changes": changes or {},
            "ip": ip or "-",
            "user_agent": user_agent or "-",
            "status": status,
        }

        if error:
            log_data["error"] = error

        if extra:
            log_data.update(extra)

        self.logger.info("", extra=log_data)

    def log_login(
        self, user_id: str | int, ip: str | None = None, user_agent: str | None = None, success: bool = True
    ) -> None:
        """Record the success or failure of a sign-in attempt."""
        self.log(
            action="login",
            user_id=user_id,
            ip=ip,
            user_agent=user_agent,
            status="success" if success else "failed",
        )

    def log_logout(self, user_id: str | int, ip: str | None = None, user_agent: str | None = None) -> None:
        """Record a sign-out event."""
        self.log(
            action="logout",
            user_id=user_id,
            ip=ip,
            user_agent=user_agent,
        )

    def log_create(
        self, user_id: str | int, resource: str, data: dict[str, Any], ip: str | None = None
    ) -> None:
        """Record a resource creation with its supplied data."""
        self.log(
            action="create",
            user_id=user_id,
            resource=resource,
            changes=data,
            ip=ip,
        )

    def log_update(
        self, user_id: str | int, resource: str, changes: dict[str, Any], ip: str | None = None
    ) -> None:
        """Record a resource update with its supplied changes."""
        self.log(
            action="update",
            user_id=user_id,
            resource=resource,
            changes=changes,
            ip=ip,
        )

    def log_delete(self, user_id: str | int, resource: str, ip: str | None = None) -> None:
        """Record a resource deletion."""
        self.log(
            action="delete",
            user_id=user_id,
            resource=resource,
            ip=ip,
        )

    def log_access_denied(self, user_id: str | int | None, resource: str, ip: str | None = None) -> None:
        """Record a denied resource access as a failed audit action."""
        self.log(
            action="access_denied",
            user_id=user_id,
            resource=resource,
            ip=ip,
            status="failed",
        )


class AuditMiddleware:
    """Record an audit event before dispatching an HTTP request."""

    def __init__(self, app: Any, logger: AuditLogger | None = None) -> None:
        self.app = app
        self.logger = logger or AuditLogger()

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request_type = import_attribute("flaxon.http", "Request")

        request = request_type(scope, receive, None)

        user_id = None
        if hasattr(request, "user") and request.user:
            if hasattr(request.user, "id"):
                user_id = request.user.id
            elif isinstance(request.user, dict):
                user_id = request.user.get("id")

        self.logger.log(
            action=f"request_{request.method.lower()}",
            user_id=user_id,
            resource=request.path,
            ip=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            extra={"method": request.method, "path": request.path},
        )

        await self.app(scope, receive, send)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client[0]
        return "-"
