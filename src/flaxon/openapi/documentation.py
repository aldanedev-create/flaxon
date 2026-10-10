from __future__ import annotations

from typing import Any


class Documentation:
    """Documentation implementation for the openapi subsystem."""

    def __init__(self, title: str = "Flaxon API", version: str = "1.0.0") -> None:
        self.title = title
        self.version = version
        self._info: dict[str, Any] = {
            "title": title,
            "version": version,
        }

    def description(self, description: str) -> Documentation:
        """Perform the description operation for documentation."""
        self._info["description"] = description
        return self

    def terms_of_service(self, url: str) -> Documentation:
        """Perform the terms of service operation for documentation."""
        self._info["termsOfService"] = url
        return self

    def contact(self, name: str, email: str | None = None, url: str | None = None) -> Documentation:
        """Perform the contact operation for documentation."""
        contact = {"name": name}
        if email:
            contact["email"] = email
        if url:
            contact["url"] = url
        self._info["contact"] = contact
        return self

    def license(self, name: str, url: str | None = None) -> Documentation:
        """Perform the license operation for documentation."""
        license_info = {"name": name}
        if url:
            license_info["url"] = url
        self._info["license"] = license_info
        return self

    def build(self) -> dict[str, Any]:
        """Perform the build operation for documentation."""
        return self._info


class DocumentationBuilder:
    """Documentation builder implementation for the openapi subsystem."""

    def __init__(self) -> None:
        self.doc = Documentation()

    def build(self) -> dict[str, Any]:
        """Perform the build operation for documentation builder."""
        return self.doc.build()

    def with_title(self, title: str) -> DocumentationBuilder:
        """Configure the title."""
        self.doc._info["title"] = title
        return self

    def with_version(self, version: str) -> DocumentationBuilder:
        """Configure the version."""
        self.doc._info["version"] = version
        return self

    def with_description(self, description: str) -> DocumentationBuilder:
        """Configure the description."""
        self.doc.description(description)
        return self

    def with_contact(self, name: str, email: str | None = None) -> DocumentationBuilder:
        """Configure the contact."""
        self.doc.contact(name, email)
        return self

    def with_license(self, name: str, url: str | None = None) -> DocumentationBuilder:
        """Configure the license."""
        self.doc.license(name, url)
        return self
