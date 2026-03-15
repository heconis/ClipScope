from __future__ import annotations

from datetime import datetime, timezone

from app.models.clip import ClipItem
from app.twitch.api_client import TwitchApiClient


CLIPS_URL = "https://api.twitch.tv/helix/clips"


class TwitchClipsService:
    def __init__(self, api_client: TwitchApiClient) -> None:
        self.api_client = api_client

    def get_clips_for_broadcaster(
        self,
        access_token: str,
        broadcaster_id: str,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        first: int = 20,
    ) -> list[ClipItem]:
        fetched_at = datetime.now(timezone.utc)
        collected: list[ClipItem] = []
        cursor: str | None = None

        while True:
            params: dict[str, str | int] = {
                "broadcaster_id": broadcaster_id,
                "first": first,
            }
            if started_at is not None:
                params["started_at"] = started_at.isoformat().replace("+00:00", "Z")
            if ended_at is not None:
                params["ended_at"] = ended_at.isoformat().replace("+00:00", "Z")
            if cursor:
                params["after"] = cursor

            payload = self.api_client.get(
                CLIPS_URL,
                access_token=access_token,
                params=params,
            )
            data = payload.get("data", [])
            collected.extend(self._to_clip(item, fetched_at) for item in data)

            cursor = payload.get("pagination", {}).get("cursor")
            if not cursor or not data:
                break

        return sorted(collected, key=lambda clip: clip.created_at, reverse=True)

    @staticmethod
    def _to_clip(payload: dict, fetched_at: datetime) -> ClipItem:
        created_at = datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00"))
        return ClipItem(
            clip_id=payload["id"],
            title=payload["title"],
            creator_name=payload["creator_name"],
            url=payload["url"],
            embed_url=payload["embed_url"],
            thumbnail_url=payload["thumbnail_url"],
            created_at=created_at,
            fetched_at=fetched_at,
            duration_seconds=float(payload.get("duration") or 0),
        )
