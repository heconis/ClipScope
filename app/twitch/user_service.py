from __future__ import annotations

import os
from typing import Any

from app.config.constants import DEFAULT_TWITCH_CLIENT_ID
from app.models.twitch_user import TwitchUser


USERS_URL = "https://api.twitch.tv/helix/users"


class TwitchUserService:
    def __init__(self, client_id: str | None = None, timeout_seconds: float = 10.0) -> None:
        self.client_id = client_id or os.getenv("TWITCH_CLIENT_ID") or DEFAULT_TWITCH_CLIENT_ID
        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.client_id)

    def get_authenticated_user(self, access_token: str) -> TwitchUser:
        import httpx

        if not self.client_id:
            raise RuntimeError("TWITCH_CLIENT_ID is not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-Id": self.client_id,
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(USERS_URL, headers=headers)
        if response.status_code >= 400:
            raise RuntimeError(f"Get Users failed: {response.status_code} {response.text}")

        data = response.json().get("data", [])
        if not data:
            raise RuntimeError("Get Users returned no authenticated user.")
        return self._to_user(data[0])

    @staticmethod
    def _to_user(payload: dict[str, Any]) -> TwitchUser:
        return TwitchUser(
            user_id=payload["id"],
            login=payload["login"],
            display_name=payload["display_name"],
            broadcaster_type=payload.get("broadcaster_type", ""),
            description=payload.get("description", ""),
            profile_image_url=payload.get("profile_image_url", ""),
            offline_image_url=payload.get("offline_image_url", ""),
            created_at=payload["created_at"],
        )
