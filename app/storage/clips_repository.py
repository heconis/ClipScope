from __future__ import annotations

from datetime import datetime

from app.models.clip import ClipItem
from app.storage.database import Database


class ClipsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get_by_id(self, clip_id: str) -> ClipItem | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT clip_id, title, creator_name, url, embed_url, thumbnail_url, created_at, fetched_at, duration_seconds, is_played
                FROM clips
                WHERE clip_id = ?
                """,
                (clip_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_clip(row)

    def list_all(self) -> list[ClipItem]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT clip_id, title, creator_name, url, embed_url, thumbnail_url, created_at, fetched_at, duration_seconds, is_played
                FROM clips
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [self._row_to_clip(row) for row in rows]

    def upsert_many(self, clips: list[ClipItem]) -> None:
        if not clips:
            return
        with self.database.connect() as connection:
            connection.executemany(
                """
                INSERT INTO clips (
                    clip_id, title, creator_name, url, embed_url, thumbnail_url, created_at, fetched_at, duration_seconds, is_played
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(clip_id) DO UPDATE SET
                    title = excluded.title,
                    creator_name = excluded.creator_name,
                    url = excluded.url,
                    embed_url = excluded.embed_url,
                    thumbnail_url = excluded.thumbnail_url,
                    created_at = excluded.created_at,
                    fetched_at = excluded.fetched_at,
                    duration_seconds = excluded.duration_seconds,
                    is_played = CASE
                        WHEN clips.is_played = 1 THEN 1
                        ELSE excluded.is_played
                    END
                """,
                [
                    (
                        clip.clip_id,
                        clip.title,
                        clip.creator_name,
                        clip.url,
                        clip.embed_url,
                        clip.thumbnail_url,
                        clip.created_at.isoformat(),
                        clip.fetched_at.isoformat(),
                        clip.duration_seconds,
                        int(clip.is_played),
                    )
                    for clip in clips
                ],
            )

    def delete_older_than(self, cutoff: datetime) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM clips WHERE created_at < ?",
                (cutoff.isoformat(),),
            )
            return cursor.rowcount

    def trim_to_limit(self, limit: int) -> int:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT clip_id
                FROM clips
                ORDER BY created_at DESC
                LIMIT -1 OFFSET ?
                """,
                (limit,),
            ).fetchall()
            if not rows:
                return 0
            connection.executemany(
                "DELETE FROM clips WHERE clip_id = ?",
                [(row["clip_id"],) for row in rows],
            )
            return len(rows)

    def delete_non_twitch_rows(self) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM clips
                WHERE url NOT LIKE 'https://www.twitch.tv/%'
                   OR embed_url NOT LIKE 'https://clips.twitch.tv/%'
                """
            )
            return cursor.rowcount

    def clear_all(self) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM clips")

    def delete_by_id(self, clip_id: str) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute("DELETE FROM clips WHERE clip_id = ?", (clip_id,))
            return cursor.rowcount

    def mark_as_played(self, clip_id: str) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "UPDATE clips SET is_played = 1 WHERE clip_id = ?",
                (clip_id,),
            )
            return cursor.rowcount

    @staticmethod
    def _row_to_clip(row) -> ClipItem:
        return ClipItem(
            clip_id=row["clip_id"],
            title=row["title"],
            creator_name=row["creator_name"],
            url=row["url"],
            embed_url=row["embed_url"],
            thumbnail_url=row["thumbnail_url"],
            created_at=datetime.fromisoformat(row["created_at"]),
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            duration_seconds=float(row["duration_seconds"]),
            is_played=bool(row["is_played"]),
        )
