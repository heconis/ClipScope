from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TwitchUser:
    user_id: str
    login: str
    display_name: str
    broadcaster_type: str
    description: str
    profile_image_url: str
    offline_image_url: str
    created_at: str
