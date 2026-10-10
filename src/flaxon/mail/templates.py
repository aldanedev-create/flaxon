from __future__ import annotations

from typing import Any

from .message import Email


class TemplateEngine:
    """Template engine implementation for the mail subsystem."""

    def __init__(self, env: Any) -> None:
        self.env = env

    def render_string(self, template: str, context: dict[str, Any]) -> str:
        """Render the string."""
        tpl = self.env.from_string(template)
        return tpl.render(**context)

    def render_file(self, template_name: str, context: dict[str, Any]) -> str:
        """Render the file."""
        tpl = self.env.get_template(template_name)
        return tpl.render(**context)

    async def render_string_async(self, template: str, context: dict[str, Any]) -> str:
        """Render the string async."""
        tpl = self.env.from_string(template)
        return await tpl.render_async(**context)

    async def render_file_async(self, template_name: str, context: dict[str, Any]) -> str:
        """Render the file async."""
        tpl = self.env.get_template(template_name)
        return await tpl.render_async(**context)


class EmailTemplate:
    """Email template implementation for the mail subsystem."""

    def __init__(
        self,
        engine: TemplateEngine,
        subject_template: str,
        body_template: str,
        html_template: str | None = None,
    ) -> None:
        self.engine = engine
        self.subject_template = subject_template
        self.body_template = body_template
        self.html_template = html_template

    def render(self, context: dict[str, Any], **kwargs: Any) -> Email:
        """Render the requested content using the supplied context."""
        subject = self.engine.render_string(self.subject_template, context)
        body = self.engine.render_string(self.body_template, context)

        html_body = None
        if self.html_template:
            html_body = self.engine.render_string(self.html_template, context)

        return Email(
            from_address=kwargs.get("from_address", ""),
            to=kwargs.get("to", []),
            cc=kwargs.get("cc", []),
            bcc=kwargs.get("bcc", []),
            subject=subject,
            body=body,
            html_body=html_body,
            headers=kwargs.get("headers", {}),
        )

    async def render_async(self, context: dict[str, Any], **kwargs: Any) -> Email:
        """Render the async."""
        subject = await self.engine.render_string_async(self.subject_template, context)
        body = await self.engine.render_string_async(self.body_template, context)

        html_body = None
        if self.html_template:
            html_body = await self.engine.render_string_async(self.html_template, context)

        return Email(
            from_address=kwargs.get("from_address", ""),
            to=kwargs.get("to", []),
            cc=kwargs.get("cc", []),
            bcc=kwargs.get("bcc", []),
            subject=subject,
            body=body,
            html_body=html_body,
            headers=kwargs.get("headers", {}),
        )
