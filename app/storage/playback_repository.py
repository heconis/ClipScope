from __future__ import annotations

from datetime import datetime

from app.models.playback import PlaybackState
from app.storage.database import Database


class PlaybackRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def load(self) -> PlaybackState:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT current_clip_id, updated_at
                FROM playback_state
                WHERE id = 1
                """
            ).fetchone()
        if row is None:
            return PlaybackState()
        return PlaybackState(
            current_clip_id=row["current_clip_id"],
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )

    def save(self, playback_state: PlaybackState) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO playback_state (id, current_clip_id, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    current_clip_id = excluded.current_clip_id,
                    updated_at = excluded.updated_at
                """,
                (
                    playback_state.current_clip_id,
                    playback_state.updated_at.isoformat() if playback_state.updated_at else None,
                ),
            )
