from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import threading

from app.models.auth import AuthState
from app.storage.auth_repository import AuthRepository
from app.twitch.auth_client import DeviceCodeResponse, TwitchAuthClient, TwitchAuthError
from app.twitch.user_service import TwitchUserService


@dataclass(slots=True)
class AuthSession:
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


class AuthService:
    _REFRESH_MARGIN_SECONDS = 120

    def __init__(
        self,
        auth_client: TwitchAuthClient,
        user_service: TwitchUserService,
        auth_repository: AuthRepository,
    ) -> None:
        self.auth_client = auth_client
        self.user_service = user_service
        self.auth_repository = auth_repository
        self._pending_session: AuthSession | None = None
        self._lock = threading.RLock()

    def get_auth_state(self) -> AuthState:
        return self.auth_repository.load() or AuthState()

    def get_pending_session(self) -> AuthSession | None:
        return self._pending_session

    def start_authentication(self) -> AuthSession:
        response = self.auth_client.start_device_code_flow()
        self._pending_session = self._to_session(response)
        return self._pending_session

    def complete_authentication(self) -> AuthState:
        if self._pending_session is None:
            raise TwitchAuthError("Authentication has not been started.")

        auth_state = self.auth_client.exchange_device_code(self._pending_session.device_code)
        if not auth_state.access_token:
            raise TwitchAuthError("No access token returned from Twitch.")

        user = self.user_service.get_authenticated_user(auth_state.access_token)
        auth_state.user_id = user.user_id
        auth_state.user_login = user.login
        auth_state.user_name = user.display_name
        auth_state.is_authenticated = True
        self.auth_repository.save(auth_state)
        self._pending_session = None
        return auth_state

    def validate_current_authentication(self) -> AuthState:
        with self._lock:
            current = self.get_auth_state()
            if not current.access_token:
                current.is_authenticated = False
                self.auth_repository.save(current)
                return current

            try:
                validation = self.auth_client.validate_access_token(current.access_token)
                current.user_id = validation.user_id
                current.user_login = validation.login
                current.is_authenticated = True
                current.scopes = validation.scopes
                current.access_token_expires_at = (
                    datetime.now(timezone.utc) + timedelta(seconds=validation.expires_in)
                )
                self.auth_repository.save(current)
                return current
            except TwitchAuthError as error:
                # Only invalidate on clear unauthorized signals. For transient
                # errors, keep current state and let callers retry later.
                if self._is_unauthorized_error(str(error)):
                    return self._invalidate_current_authentication(current)
                return current

    def ensure_valid_authentication(self, force_refresh: bool = False) -> AuthState:
        with self._lock:
            current = self.get_auth_state()

            if force_refresh:
                refreshed = self._refresh_current_access_token(current)
                if refreshed is not None:
                    return refreshed
                if current.access_token:
                    return self.validate_current_authentication()
                return current

            if self._should_refresh_access_token(current):
                refreshed = self._refresh_current_access_token(current)
                if refreshed is not None:
                    return refreshed

            if current.access_token and current.access_token_expires_at is None:
                # Legacy records may not have expiry persisted; backfill once.
                return self.validate_current_authentication()

            return current

    def clear_authentication(self) -> None:
        self.auth_repository.save(AuthState())
        self._pending_session = None

    def _should_refresh_access_token(self, current: AuthState) -> bool:
        if not current.access_token:
            return False
        if not current.refresh_token:
            return False
        if current.access_token_expires_at is None:
            return True
        return (
            datetime.now(timezone.utc)
            >= current.access_token_expires_at - timedelta(seconds=self._REFRESH_MARGIN_SECONDS)
        )

    def _refresh_current_access_token(self, current: AuthState) -> AuthState | None:
        if not current.refresh_token:
            return None
        try:
            refreshed = self.auth_client.refresh_access_token(
                refresh_token=current.refresh_token,
                scopes=current.scopes,
            )
        except TwitchAuthError as error:
            message = str(error).lower()
            if self._is_unauthorized_error(message) or "invalid refresh token" in message:
                return self._invalidate_current_authentication(current)
            return None

        if not refreshed.access_token or not refreshed.refresh_token:
            return self._invalidate_current_authentication(current)

        current.access_token = refreshed.access_token
        current.refresh_token = refreshed.refresh_token
        current.access_token_expires_at = refreshed.access_token_expires_at
        if refreshed.scopes:
            current.scopes = refreshed.scopes
        current.is_authenticated = True

        if not current.user_id or not current.user_login:
            try:
                user = self.user_service.get_authenticated_user(current.access_token)
                current.user_id = user.user_id
                current.user_login = user.login
                current.user_name = user.display_name
            except Exception:
                # Keep refreshed token usable even if Get Users temporarily fails.
                pass

        self.auth_repository.save(current)
        return current

    def _invalidate_current_authentication(self, current: AuthState) -> AuthState:
        current.is_authenticated = False
        current.access_token = None
        current.refresh_token = None
        current.access_token_expires_at = None
        self.auth_repository.save(current)
        return current

    @staticmethod
    def _is_unauthorized_error(message: str) -> bool:
        lower = message.lower()
        return " 401 " in lower or lower.startswith("twitch validate request failed: 401")

    @staticmethod
    def _to_session(response: DeviceCodeResponse) -> AuthSession:
        return AuthSession(
            device_code=response.device_code,
            user_code=response.user_code,
            verification_uri=response.verification_uri,
            expires_in=response.expires_in,
            interval=response.interval,
        )
