from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass


@dataclass(slots=True)
class AppSettings:
    polling_interval_seconds: int
    local_server_port: int
    max_clip_count: int
    retention_days: int
    window_width: int = 1440
    window_height: int = 900

    def copy(self) -> "AppSettings":
        return AppSettings(**asdict(self))
