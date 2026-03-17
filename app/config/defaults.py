from __future__ import annotations

from app.models.settings import AppSettings


DEFAULT_SETTINGS = AppSettings(
    polling_interval_seconds=10,
    local_server_port=8787,
    max_clip_count=100,
    retention_days=30,
    always_on_top=True,
    play_sound_on_new_clip=True,
    theme_mode="light",
    window_width=1440,
    window_height=900,
)


def build_default_settings() -> AppSettings:
    return DEFAULT_SETTINGS.copy()
