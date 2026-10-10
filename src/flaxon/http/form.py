"""
Form data handling for Flaxon.

This module provides utilities for parsing and handling form data from HTTP requests.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs

from flaxon._imports import import_attribute
from flaxon.exceptions import BadRequest


class FormData:
    """
    Form data container.

    This class represents parsed form data from a request.

    Example:
        ```python
        form = await FormData.from_request(request)
        name = form.get("name")
        email = form.get("email")
        ```
    """

    def __init__(self, data: dict[str, list[str]] | None = None) -> None:
        """
        Initialize form data.

        Args:
            data: The form data dictionary.
        """
        self._data: dict[str, list[str]] = data or {}

    def get(self, key: str, default: Any = None) -> str | None:
        """
        Get a form value.

        Args:
            key: The form field key.
            default: The default value if not found.

        Returns:
            The form value or default.
        """
        values = self._data.get(key)
        if not values:
            return default
        return values[0]

    def get_list(self, key: str) -> list[str]:
        """
        Get a form value as a list.

        Args:
            key: The form field key.

        Returns:
            A list of values.
        """
        return self._data.get(key, [])

    def get_int(self, key: str, default: int | None = None) -> int | None:
        """
        Get a form value as an integer.

        Args:
            key: The form field key.
            default: The default value if not found.

        Returns:
            The integer value or default.

        Raises:
            ValueError: If the value cannot be converted to int.
        """
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"Form field '{key}' must be an integer") from exc

    def get_float(self, key: str, default: float | None = None) -> float | None:
        """
        Get a form value as a float.

        Args:
            key: The form field key.
            default: The default value if not found.

        Returns:
            The float value or default.

        Raises:
            ValueError: If the value cannot be converted to float.
        """
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"Form field '{key}' must be a float") from exc

    def get_bool(self, key: str, default: bool | None = None) -> bool | None:
        """
        Get a form value as a boolean.

        Args:
            key: The form field key.
            default: The default value if not found.

        Returns:
            The boolean value or default.
        """
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in {"true", "1", "yes", "on"}

    def get_json(self, key: str) -> Any:
        """
        Get a form value as JSON.

        Args:
            key: The form field key.

        Returns:
            The parsed JSON value.

        Raises:
            ValueError: If the value is not valid JSON.
        """
        value = self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Form field '{key}' must be valid JSON") from exc

    def get_all(self) -> dict[str, list[str]]:
        """
        Get all form data.

        Returns:
            A dictionary of all form fields.
        """
        return dict(self._data)

    def to_dict(self) -> dict[str, str | list[str]]:
        """
        Convert to a dictionary.

        Returns:
            A dictionary of form fields.
        """
        result: dict[str, str | list[str]] = {}
        for key, values in self._data.items():
            result[key] = values[0] if len(values) == 1 else values
        return result

    def keys(self) -> list[str]:
        """Get all form field keys."""
        return list(self._data.keys())

    def values(self) -> list[list[str]]:
        """Get all form field values."""
        return list(self._data.values())

    def items(self) -> list[tuple[str, list[str]]]:
        """Get all form field items."""
        return list(self._data.items())

    def __contains__(self, key: str) -> bool:
        """Check if a form field exists."""
        return key in self._data

    def __len__(self) -> int:
        """Get the number of form fields."""
        return len(self._data)

    def __repr__(self) -> str:
        """Get a string representation of the form data."""
        return f"FormData({self._data})"

    @classmethod
    async def from_request(cls, request: Any) -> FormData:
        """
        Parse form data from a request.

        Args:
            request: The request object.

        Returns:
            A FormData instance.

        Raises:
            BadRequest: If the content type is not form data.
        """
        content_type = request.headers.get("content-type", "")

        if "application/x-www-form-urlencoded" in content_type:
            text = await request.text()
            parsed = parse_qs(text, keep_blank_values=True)
            return cls(parsed)

        if "multipart/form-data" in content_type:
            return await cls._parse_multipart(request, content_type)

        raise BadRequest("Content-Type must be application/x-www-form-urlencoded or multipart/form-data")

    @classmethod
    async def _parse_multipart(cls, request: Any, content_type: str) -> FormData:
        """Parse multipart form data."""
        multipart_parser_type = import_attribute("flaxon.http.uploads", "MultipartParser")

        parser = multipart_parser_type(content_type)
        return await parser.parse(request)
