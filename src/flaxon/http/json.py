"""
JSON handling for Flaxon.

This module provides JSON encoding and decoding utilities.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from flaxon.exceptions import BadRequest


class FlaxonJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for Flaxon.

    This encoder handles dataclasses, datetime objects, decimals, and
    objects with to_dict methods.
    """

    def default(self, value: Any) -> Any:
        """
        Encode custom types to JSON.

        Args:
            value: The value to encode.

        Returns:
            The JSON-serializable value.

        Raises:
            TypeError: If the value cannot be encoded.
        """
        if is_dataclass(value):
            return asdict(value)

        if isinstance(value, (datetime, date)):
            return value.isoformat()

        if isinstance(value, Decimal):
            return float(value)

        if hasattr(value, "to_dict"):
            return value.to_dict()

        if hasattr(value, "model_dump"):
            return value.model_dump()

        return super().default(value)


class FlaxonJSONDecoder(json.JSONDecoder):
    """Custom JSON decoder for Flaxon."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the decoder."""
        super().__init__(*args, object_hook=self.object_hook, **kwargs)

    def object_hook(self, obj: dict[str, Any]) -> dict[str, Any]:
        """
        Hook for decoding JSON objects.

        Args:
            obj: The JSON object.

        Returns:
            The decoded object.
        """
        return obj


def dumps(data: Any, **kwargs: Any) -> str:
    """
    Serialize data to JSON.

    Args:
        data: The data to serialize.
        **kwargs: Additional arguments to pass to json.dumps.

    Returns:
        The JSON string.
    """
    return json.dumps(data, cls=FlaxonJSONEncoder, ensure_ascii=False, separators=(",", ":"), **kwargs)


def loads(data: str | bytes, **kwargs: Any) -> Any:
    """
    Deserialize JSON data.

    Args:
        data: The JSON data to deserialize.
        **kwargs: Additional arguments to pass to json.loads.

    Returns:
        The deserialized data.

    Raises:
        BadRequest: If the JSON is invalid.
    """
    try:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return json.loads(data, cls=FlaxonJSONDecoder, **kwargs)
    except json.JSONDecodeError as exc:
        raise BadRequest("Invalid JSON data") from exc


def load_from_request(request: Any) -> Any:
    """
    Load JSON data from a request.

    Args:
        request: The request object.

    Returns:
        The parsed JSON data.

    Raises:
        BadRequest: If the JSON is invalid.
    """
    if not hasattr(request, "json"):
        raise BadRequest("Request does not support JSON parsing")

    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            return asyncio.create_task(request.json())
        return request.json()
    except AttributeError:
        return request.json()


class JSONAPI:
    """
    JSON API utilities.

    This class provides utilities for building JSON APIs.
    """

    @staticmethod
    def success(data: Any, status_code: int = 200) -> dict[str, Any]:
        """
        Create a success response.

        Args:
            data: The response data.
            status_code: The HTTP status code.

        Returns:
            A success response dictionary.
        """
        return {
            "success": True,
            "status": status_code,
            "data": data,
        }

    @staticmethod
    def error(
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create an error response.

        Args:
            code: The error code.
            message: The error message.
            status_code: The HTTP status code.
            details: Additional error details.

        Returns:
            An error response dictionary.
        """
        response: dict[str, Any] = {
            "success": False,
            "status": status_code,
            "error": {
                "code": code,
                "message": message,
            },
        }
        if details:
            response["error"]["details"] = details
        return response

    @staticmethod
    def paginate(
        items: list[Any],
        page: int,
        per_page: int,
        total: int | None = None,
    ) -> dict[str, Any]:
        """
        Create a paginated response.

        Args:
            items: The items for the current page.
            page: The current page number.
            per_page: The number of items per page.
            total: The total number of items.

        Returns:
            A paginated response dictionary.
        """
        total = total or len(items)
        total_pages = (total + per_page - 1) // per_page

        return {
            "success": True,
            "data": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }
