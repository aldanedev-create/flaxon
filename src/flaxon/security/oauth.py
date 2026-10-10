from __future__ import annotations

import secrets
import urllib.parse
from typing import Any

from flaxon._imports import import_module


class OAuth2Provider:
    """Oauth2 provider implementation for the security subsystem."""

    def __init__(  # noqa: PLR0917 - preserve existing positional API
        self,
        client_id: str,
        client_secret: str,
        authorization_endpoint: str,
        token_endpoint: str,
        redirect_uri: str,
        scope: str = "openid profile email",
        state: str | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorization_endpoint = authorization_endpoint
        self.token_endpoint = token_endpoint
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.state = state or secrets.token_urlsafe(32)

    def get_authorization_url(self, additional_params: dict[str, Any] | None = None) -> str:
        """Return the authorization url."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scope,
            "state": self.state,
            **(additional_params or {}),
        }
        return f"{self.authorization_endpoint}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Perform the exchange code operation for oauth2 provider."""
        httpx = import_module("httpx")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_endpoint, data=data)
            response.raise_for_status()
            return response.json()

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Perform the refresh token operation for oauth2 provider."""
        httpx = import_module("httpx")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_endpoint, data=data)
            response.raise_for_status()
            return response.json()


class OAuth2Backend:
    """Provide oauth2 storage for flaxon operations."""

    def __init__(self, providers: dict[str, OAuth2Provider] | None = None) -> None:
        self.providers = providers or {}

    def register_provider(self, name: str, provider: OAuth2Provider) -> None:
        """Register the provider."""
        self.providers[name] = provider

    def get_provider(self, name: str) -> OAuth2Provider | None:
        """Return the provider."""
        return self.providers.get(name)

    def get_authorization_url(self, provider_name: str) -> str:
        """Return the authorization url."""
        provider = self.get_provider(provider_name)
        if provider is None:
            raise ValueError(f"Provider '{provider_name}' not found")
        return provider.get_authorization_url()

    async def authenticate(self, provider_name: str, code: str) -> dict[str, Any]:
        """Resolve a user or identity using the configured authentication backend."""
        provider = self.get_provider(provider_name)
        if provider is None:
            raise ValueError(f"Provider '{provider_name}' not found")
        return await provider.exchange_code(code)
