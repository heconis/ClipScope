from __future__ import annotations

from dataclasses import dataclass

from app.models.auth import AuthState
from app.models.twitch_user import TwitchUser
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
            self.auth_repository.save(current)
            return current
        except TwitchAuthError:
            # Token is no longer valid. Keep the record but mark it unauthenticated.
            current.is_authenticated = False
            current.access_token = None
            current.refresh_token = None
            self.auth_repository.save(current)
            return current

    def clear_authentication(self) -> None:
        self.auth_repository.save(AuthState())
        self._pending_session = None

    @staticmethod
    def _to_session(response: DeviceCodeResponse) -> AuthSession:
        return AuthSession(
            device_code=response.device_code,
            user_code=response.user_code,
            verification_uri=response.verification_uri,
            expires_in=response.expires_in,
            interval=response.interval,
        )
