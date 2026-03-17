from __future__ import annotations

from app.models.settings import AppSettings
from app.storage.database import Database


class SettingsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def load(self) -> AppSettings | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT polling_interval_seconds, local_server_port, max_clip_count,
                       retention_days, always_on_top, play_sound_on_new_clip, theme_mode,
                       window_width, window_height
                FROM settings
                WHERE id = 1
                """
            ).fetchone()
        if row is None:
            return None
        return AppSettings(
            polling_interval_seconds=row["polling_interval_seconds"],
            local_server_port=row["local_server_port"],
            max_clip_count=row["max_clip_count"],
            retention_days=row["retention_days"],
            always_on_top=bool(row["always_on_top"]),
            play_sound_on_new_clip=bool(row["play_sound_on_new_clip"]),
            theme_mode=row["theme_mode"] or "light",
            window_width=row["window_width"],
            window_height=row["window_height"],
        )

    def save(self, settings: AppSettings) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO settings (
                    id, polling_interval_seconds, local_server_port, max_clip_count,
                    retention_days, always_on_top, play_sound_on_new_clip, theme_mode,
                    window_width, window_height
                )
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    polling_interval_seconds = excluded.polling_interval_seconds,
                    local_server_port = excluded.local_server_port,
                    max_clip_count = excluded.max_clip_count,
                    retention_days = excluded.retention_days,
                    always_on_top = excluded.always_on_top,
                    play_sound_on_new_clip = excluded.play_sound_on_new_clip,
                    theme_mode = excluded.theme_mode,
                    window_width = excluded.window_width,
                    window_height = excluded.window_height
                """,
                (
                    settings.polling_interval_seconds,
                    settings.local_server_port,
                    settings.max_clip_count,
                    settings.retention_days,
                    1 if settings.always_on_top else 0,
                    1 if settings.play_sound_on_new_clip else 0,
                    settings.theme_mode,
                    settings.window_width,
                    settings.window_height,
                ),
            )
