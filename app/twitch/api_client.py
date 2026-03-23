from __future__ import annotations

import os
from typing import Any

from app.config.constants import DEFAULT_TWITCH_CLIENT_ID


class TwitchApiError(RuntimeError):
    """Raised when a Twitch API request fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class TwitchApiClient:
    def __init__(self, client_id: str | None = None, timeout_seconds: float = 10.0) -> None:
        self.client_id = client_id or os.getenv("TWITCH_CLIENT_ID") or DEFAULT_TWITCH_CLIENT_ID
        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.client_id)

    def get(
        self,
        url: str,
        access_token: str,
        params: dict[str, str | int] | None = None,
    ) -> dict[str, Any]:
        import httpx

        if not self.client_id:
            raise TwitchApiError("TWITCH_CLIENT_ID is not configured.")
        if not access_token:
            raise TwitchApiError("A user access token is required.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-Id": self.client_id,
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(url, headers=headers, params=params)
        if response.status_code >= 400:
            raise TwitchApiError(
                f"Twitch API request failed: {response.status_code} {response.text}",
                status_code=response.status_code,
                response_text=response.text,
            )
        return response.json()
