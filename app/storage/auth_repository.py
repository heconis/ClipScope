from __future__ import annotations

import json
from datetime import datetime

from app.models.auth import AuthState
from app.storage.database import Database


class AuthRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def load(self) -> AuthState | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT access_token, refresh_token, user_id, user_login,
                       user_name, scopes, is_authenticated, access_token_expires_at
                FROM auth_state
                WHERE id = 1
                """
            ).fetchone()
        if row is None:
            return None
        return AuthState(
            access_token=row["access_token"],
            refresh_token=row["refresh_token"],
            access_token_expires_at=(
                datetime.fromisoformat(row["access_token_expires_at"])
                if row["access_token_expires_at"]
                else None
            ),
            user_id=row["user_id"],
            user_login=row["user_login"],
            user_name=row["user_name"],
            is_authenticated=bool(row["is_authenticated"]),
            scopes=tuple(json.loads(row["scopes"])),
        )

    def save(self, auth_state: AuthState) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO auth_state (
                    id, access_token, refresh_token, access_token_expires_at,
                    user_id, user_login, user_name, scopes, is_authenticated
                )
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    access_token_expires_at = excluded.access_token_expires_at,
                    user_id = excluded.user_id,
                    user_login = excluded.user_login,
                    user_name = excluded.user_name,
                    scopes = excluded.scopes,
                    is_authenticated = excluded.is_authenticated
                """,
                (
                    auth_state.access_token,
                    auth_state.refresh_token,
                    (
                        auth_state.access_token_expires_at.isoformat()
                        if auth_state.access_token_expires_at
                        else None
                    ),
                    auth_state.user_id,
                    auth_state.user_login,
                    auth_state.user_name,
                    json.dumps(list(auth_state.scopes)),
                    int(auth_state.is_authenticated),
                ),
            )
