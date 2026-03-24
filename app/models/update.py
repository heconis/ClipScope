from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UpdateCheckResult:
    current_version: str
    latest_version: str
    is_update_available: bool
    download_url: str
    release_notes_url: str | None = None
    message: str | None = None
