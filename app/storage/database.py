from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path

from app.config.constants import APP_NAME, DEFAULT_DATABASE_FILENAME


class Database:
    def __init__(self, db_path: Path | None = None) -> None:
        default_path = self._resolve_default_db_path()
        self.db_path = (db_path or default_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy_db_if_needed()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    polling_interval_seconds INTEGER NOT NULL,
                    local_server_port INTEGER NOT NULL,
                    max_clip_count INTEGER NOT NULL,
                    retention_days INTEGER NOT NULL,
                    window_width INTEGER NOT NULL,
                    window_height INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS auth_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    access_token TEXT,
                    refresh_token TEXT,
                    user_id TEXT,
                    user_login TEXT,
                    user_name TEXT,
                    scopes TEXT NOT NULL DEFAULT '[]',
                    is_authenticated INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS clips (
                    clip_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    creator_name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    embed_url TEXT NOT NULL,
                    thumbnail_url TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    duration_seconds REAL NOT NULL DEFAULT 0,
                    is_played INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS playback_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    current_clip_id TEXT,
                    updated_at TEXT
                );
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(auth_state)").fetchall()
            }
            if "scopes" not in columns:
                connection.execute(
                    "ALTER TABLE auth_state ADD COLUMN scopes TEXT NOT NULL DEFAULT '[]'"
                )
            clip_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(clips)").fetchall()
            }
            if "is_played" not in clip_columns:
                connection.execute(
                    "ALTER TABLE clips ADD COLUMN is_played INTEGER NOT NULL DEFAULT 0"
                )
            if "duration_seconds" not in clip_columns:
                connection.execute(
                    "ALTER TABLE clips ADD COLUMN duration_seconds REAL NOT NULL DEFAULT 0"
                )

    @staticmethod
    def _resolve_default_db_path() -> Path:
        override_path = os.getenv("CLIPSCOPE_DB_PATH")
        if override_path:
            return Path(override_path).expanduser()

        appdata_dir = os.getenv("APPDATA")
        if appdata_dir:
            return Path(appdata_dir) / APP_NAME / DEFAULT_DATABASE_FILENAME

        # Fallback for non-Windows or environments without APPDATA.
        return Path.home() / ".local" / "share" / APP_NAME / DEFAULT_DATABASE_FILENAME

    def _migrate_legacy_db_if_needed(self) -> None:
        legacy_path = Path(__file__).resolve().parents[2] / DEFAULT_DATABASE_FILENAME
        if self.db_path.exists() or not legacy_path.exists() or legacy_path == self.db_path:
            return
        try:
            shutil.copy2(legacy_path, self.db_path)
        except OSError:
            # If migration fails, continue with a fresh database at the new location.
            return
