from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PlaybackState:
    current_clip_id: str | None = None
    updated_at: datetime | None = None
