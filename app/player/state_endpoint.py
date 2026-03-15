from __future__ import annotations

from app.clips.selection_service import SelectionService


class PlayerStateEndpoint:
    def __init__(self, selection_service: SelectionService) -> None:
        self.selection_service = selection_service

    def build_payload(self) -> dict[str, str | float | None]:
        state = self.selection_service.get_state()
        clip = self.selection_service.get_selected_clip()
        return {
            "clip_id": state.current_clip_id,
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
            "embed_url": clip.embed_url if clip else None,
            "duration_seconds": clip.duration_seconds if clip else None,
        }
