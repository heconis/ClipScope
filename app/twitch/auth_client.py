from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from app.config.constants import DEFAULT_TWITCH_CLIENT_ID
from app.models.auth import AuthState


DEVICE_URL = "https://id.twitch.tv/oauth2/device"
TOKEN_URL = "https://id.twitch.tv/oauth2/token"
VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"


class TwitchAuthError(RuntimeError):
    """Raised when Twitch authentication fails."""


@dataclass(slots=True)
class DeviceCodeResponse:
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


@dataclass(slots=True)
class TokenValidation:
    client_id: str
    login: str
    user_id: str
    expires_in: int
    scopes: tuple[str, ...]


class TwitchAuthClient:
    def __init__(self, client_id: str | None = None, timeout_seconds: float = 10.0) -> None:
        self.client_id = client_id or os.getenv("TWITCH_CLIENT_ID") or DEFAULT_TWITCH_CLIENT_ID
        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.client_id)

    def start_device_code_flow(self, scopes: tuple[str, ...] = ()) -> DeviceCodeResponse:
        self._ensure_client_id()
        response = self._post_form(
            DEVICE_URL,
            {
                "client_id": self.client_id,
                "scopes": " ".join(scopes),
            },
        )
        return DeviceCodeResponse(
            device_code=response["device_code"],
            user_code=response["user_code"],
            verification_uri=response["verification_uri"],
            expires_in=int(response["expires_in"]),
            interval=int(response["interval"]),
        )

    def exchange_device_code(self, device_code: str, scopes: tuple[str, ...] = ()) -> AuthState:
        self._ensure_client_id()
        response = self._post_form(
            TOKEN_URL,
            {
                "client_id": self.client_id,
                "scope": " ".join(scopes),
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        resolved_scopes = self._normalize_scopes(response.get("scope"))
        return AuthState(
            access_token=response.get("access_token"),
            refresh_token=response.get("refresh_token"),
            is_authenticated=bool(response.get("access_token")),
            scopes=resolved_scopes,
        )

    def validate_access_token(self, access_token: str) -> TokenValidation:
        headers = {"Authorization": f"OAuth {access_token}"}
        response = self._get_json(VALIDATE_URL, headers=headers)
        resolved_scopes = self._normalize_scopes(response.get("scopes"))
        return TokenValidation(
            client_id=response["client_id"],
            login=response["login"],
            user_id=response["user_id"],
            expires_in=int(response["expires_in"]),
            scopes=resolved_scopes,
        )

    def _ensure_client_id(self) -> None:
        if not self.client_id:
            raise TwitchAuthError("TWITCH_CLIENT_ID is not configured.")

    def _post_form(self, url: str, form_data: dict[str, str]) -> dict[str, Any]:
        import httpx

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(url, data=form_data)
        if response.status_code >= 400:
            raise TwitchAuthError(f"Twitch auth request failed: {response.status_code} {response.text}")
        return response.json()

    def _get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        import httpx

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(url, headers=headers)
        if response.status_code >= 400:
            raise TwitchAuthError(f"Twitch validate request failed: {response.status_code} {response.text}")
        return response.json()

    @staticmethod
    def _normalize_scopes(raw_scopes: Any) -> tuple[str, ...]:
        if raw_scopes is None:
            return ()
        if isinstance(raw_scopes, str):
            return tuple(scope for scope in raw_scopes.split() if scope)
        try:
            return tuple(raw_scopes)
        except TypeError:
            return ()
