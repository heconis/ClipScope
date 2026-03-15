from __future__ import annotations

from datetime import datetime, timezone

from app.models.clip import ClipItem
from app.models.playback import PlaybackState
from app.storage.clips_repository import ClipsRepository
from app.storage.playback_repository import PlaybackRepository


class SelectionService:
    def __init__(self, clips_repository: ClipsRepository, playback_repository: PlaybackRepository) -> None:
        self.clips_repository = clips_repository
        self.playback_repository = playback_repository

    def get_state(self) -> PlaybackState:
        return self.playback_repository.load()

    def get_selected_clip_id(self) -> str | None:
        return self.get_state().current_clip_id

    def get_selected_clip(self) -> ClipItem | None:
        clip_id = self.get_selected_clip_id()
        if clip_id is None:
            return None
        return self.clips_repository.get_by_id(clip_id)

    def select_clip(self, clip_id: str) -> PlaybackState:
        clip = self.clips_repository.get_by_id(clip_id)
        if clip is None:
            raise ValueError(f"Clip not found: {clip_id}")
        self.clips_repository.mark_as_played(clip_id)
        playback_state = PlaybackState(
            current_clip_id=clip.clip_id,
            updated_at=datetime.now(timezone.utc),
        )
        self.playback_repository.save(playback_state)
        return playback_state

    def clear_selection(self) -> PlaybackState:
        playback_state = PlaybackState(
            current_clip_id=None,
            updated_at=datetime.now(timezone.utc),
        )
        self.playback_repository.save(playback_state)
        return playback_state
