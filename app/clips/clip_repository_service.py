from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.clip import ClipItem
from app.storage.clips_repository import ClipsRepository


class ClipRepositoryService:
    def __init__(
        self,
        repository: ClipsRepository,
        max_clip_count: int = 100,
        retention_days: int = 30,
    ) -> None:
        self.repository = repository
        self.max_clip_count = max_clip_count
        self.retention_days = retention_days

    def list_clips(self) -> list[ClipItem]:
        return self.repository.list_all()

    def latest_clip_created_at(self) -> datetime | None:
        return self.repository.get_latest_created_at()

    def merge_clips(self, clips: list[ClipItem]) -> list[ClipItem]:
        deduped = self._dedupe_by_clip_id(clips)
        sorted_clips = sorted(deduped.values(), key=lambda clip: clip.created_at, reverse=True)
        self.repository.upsert_many(sorted_clips)
        self.enforce_retention_policy()
        return self.list_clips()

    def enforce_retention_policy(self) -> None:
        self.repository.delete_non_twitch_rows()
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        self.repository.delete_older_than(cutoff)
        self.repository.trim_to_limit(self.max_clip_count)

    def reconfigure(self, max_clip_count: int, retention_days: int) -> None:
        self.max_clip_count = max_clip_count
        self.retention_days = retention_days
        self.enforce_retention_policy()

    def delete_clip(self, clip_id: str) -> bool:
        deleted_count = self.repository.delete_by_id(clip_id)
        return deleted_count > 0

    def mark_clip_as_played(self, clip_id: str) -> bool:
        updated_count = self.repository.mark_as_played(clip_id)
        return updated_count > 0

    @staticmethod
    def _dedupe_by_clip_id(clips: list[ClipItem]) -> dict[str, ClipItem]:
        deduped: dict[str, ClipItem] = {}
        for clip in clips:
            existing = deduped.get(clip.clip_id)
            if existing is None or clip.fetched_at > existing.fetched_at:
                deduped[clip.clip_id] = clip
        return deduped
