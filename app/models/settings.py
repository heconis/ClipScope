from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass


@dataclass(slots=True)
class AppSettings:
    polling_interval_seconds: int
    local_server_port: int
    max_clip_count: int
    retention_days: int
    always_on_top: bool = True
    play_sound_on_new_clip: bool = True
    auto_update_check: bool = True
    theme_mode: str = "light"
    window_width: int = 1440
    window_height: int = 900

    def copy(self) -> "AppSettings":
        return AppSettings(**asdict(self))
