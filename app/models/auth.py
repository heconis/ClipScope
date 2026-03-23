from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class AuthState:
    access_token: str | None = None
    refresh_token: str | None = None
    access_token_expires_at: datetime | None = None
    user_id: str | None = None
    user_login: str | None = None
    user_name: str | None = None
    is_authenticated: bool = False
    scopes: tuple[str, ...] = ()
