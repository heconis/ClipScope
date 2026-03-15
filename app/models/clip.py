from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ClipItem:
    clip_id: str
    title: str
    creator_name: str
    url: str
    embed_url: str
    thumbnail_url: str
    created_at: datetime
    fetched_at: datetime
    duration_seconds: float = 0.0
    is_played: bool = False
