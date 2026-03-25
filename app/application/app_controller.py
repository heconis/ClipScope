from __future__ import annotations

import threading

from app.application.monitor_service import MonitorService, MonitorStatus
from app.application.settings_service import SettingsService
from app.application.update_service import UpdateService
from app.application.auth_service import AuthService, AuthSession
from app.clips.clip_repository_service import ClipRepositoryService
from app.clips.selection_service import SelectionService
from app.config.constants import DEFAULT_PLAYER_PATH
from app.models.auth import AuthState
from app.models.clip import ClipItem
from app.models.settings import AppSettings
from app.models.update import UpdateCheckResult
from app.player.server import PlayerServer
from app.storage.auth_repository import AuthRepository
from app.storage.database import Database


class AppController:
    def __init__(
        self,
        settings_service: SettingsService,
        auth_service: AuthService,
        auth_repository: AuthRepository,
        clip_repository_service: ClipRepositoryService,
        selection_service: SelectionService,
        monitor_service: MonitorService,
        update_service: UpdateService,
        player_server: PlayerServer,
        database: Database,
    ) -> None:
        self.settings_service = settings_service
        self.auth_service = auth_service
        self.auth_repository = auth_repository
        self.clip_repository_service = clip_repository_service
        self.selection_service = selection_service
        self.monitor_service = monitor_service
        self.update_service = update_service
        self.player_server = player_server
        self.database = database
        self.settings = self.settings_service.load()
        self.auth_state = self.auth_repository.load() or AuthState()
        self._startup_auth_validation_thread: threading.Thread | None = None

    def bootstrap(self) -> None:
        self.settings = self.settings_service.load()
        self.auth_state = self.auth_service.get_auth_state()
        self._start_startup_auth_validation()
        self.monitor_service.configure(self.settings.polling_interval_seconds)
        self.player_server.start()

    def _start_startup_auth_validation(self) -> None:
        current_auth = self.auth_state
        if not current_auth.access_token and not current_auth.refresh_token:
            return

        def _validate() -> None:
            try:
                # At startup, prefer auto-refresh when the token is near/over expiry.
                # Falls back to validation for legacy records.
                self.auth_state = self.auth_service.ensure_valid_authentication(
                    force_refresh=bool(current_auth.refresh_token and not current_auth.access_token)
                )
            except Exception:
                # Keep startup resilient on transient network errors.
                self.auth_state = current_auth

        self._startup_auth_validation_thread = threading.Thread(
            target=_validate,
            name="startup-auth-validation",
            daemon=True,
        )
        self._startup_auth_validation_thread.start()

    def shutdown(self) -> None:
        self.monitor_service.stop()
        try:
            self.clear_selection()
        except Exception:
            # Keep shutdown resilient even if playback state cleanup fails.
            pass
        self.player_server.stop()

    def get_settings(self) -> AppSettings:
        self.settings = self.settings_service.load()
        return self.settings

    def save_settings(self, settings: AppSettings) -> AppSettings:
        previous_port = self.settings.local_server_port
        self.settings = self.settings_service.save(settings)
        self.monitor_service.configure(self.settings.polling_interval_seconds)
        self.clip_repository_service.reconfigure(
            self.settings.max_clip_count,
            self.settings.retention_days,
        )
        if self.settings.local_server_port != previous_port:
            self.player_server.reconfigure(self.settings.local_server_port)
        return self.settings

    def reset_settings(self) -> AppSettings:
        previous_port = self.settings.local_server_port
        self.settings = self.settings_service.reset()
        self.monitor_service.configure(self.settings.polling_interval_seconds)
        self.clip_repository_service.reconfigure(
            self.settings.max_clip_count,
            self.settings.retention_days,
        )
        if self.settings.local_server_port != previous_port:
            self.player_server.reconfigure(self.settings.local_server_port)
        return self.settings

    def get_default_settings(self) -> AppSettings:
        return self.settings_service.get_defaults()

    def get_auth_state(self) -> AuthState:
        self.auth_state = self.auth_service.get_auth_state()
        return self.auth_state

    def get_auth_state_for_twitch_api(self, force_refresh: bool = False) -> AuthState:
        self.auth_state = self.auth_service.ensure_valid_authentication(force_refresh=force_refresh)
        return self.auth_state

    def require_broadcaster_id(self) -> str:
        auth_state = self.get_auth_state()
        if not auth_state.is_authenticated or not auth_state.user_id:
            raise RuntimeError("最初にTwitch認証を完了してください。")
        return auth_state.user_id

    def get_pending_auth_session(self) -> AuthSession | None:
        return self.auth_service.get_pending_session()

    def start_authentication(self) -> AuthSession:
        return self.auth_service.start_authentication()

    def complete_authentication(self) -> AuthState:
        self.auth_state = self.auth_service.complete_authentication()
        return self.auth_state

    def validate_authentication(self) -> AuthState:
        self.auth_state = self.auth_service.validate_current_authentication()
        return self.auth_state

    def clear_authentication(self) -> None:
        self.auth_service.clear_authentication()
        self.auth_state = AuthState()

    def list_clips(self) -> list[ClipItem]:
        return self.clip_repository_service.list_clips()

    def get_selected_clip(self) -> ClipItem | None:
        return self.selection_service.get_selected_clip()

    def get_selected_clip_id(self) -> str | None:
        return self.selection_service.get_selected_clip_id()

    def select_clip(self, clip_id: str) -> None:
        self.selection_service.select_clip(clip_id)

    def clear_selection(self) -> None:
        self.selection_service.clear_selection()

    def delete_clip(self, clip_id: str) -> bool:
        selected_clip_id = self.get_selected_clip_id()
        deleted = self.clip_repository_service.delete_clip(clip_id)
        if deleted and selected_clip_id == clip_id:
            self.clear_selection()
        return deleted

    def get_monitor_status(self) -> MonitorStatus:
        return self.monitor_service.get_status()

    def start_monitoring(self, broadcaster_id: str | None = None) -> None:
        resolved_broadcaster_id = broadcaster_id or self.require_broadcaster_id()
        self.monitor_service.start(
            auth_state_provider=self.get_auth_state_for_twitch_api,
            broadcaster_id=resolved_broadcaster_id,
            force_refresh_auth_state=lambda: self.get_auth_state_for_twitch_api(force_refresh=True),
        )

    def stop_monitoring(self) -> None:
        self.monitor_service.stop()

    def refresh_clips(self, broadcaster_id: str | None = None) -> list[ClipItem]:
        resolved_broadcaster_id = broadcaster_id or self.require_broadcaster_id()
        return self.monitor_service.run_once(
            self.get_auth_state_for_twitch_api(),
            resolved_broadcaster_id,
            force_refresh_auth_state=lambda: self.get_auth_state_for_twitch_api(force_refresh=True),
        )

    def get_player_url(self) -> str:
        return f"http://{self.player_server.host}:{self.player_server.port}{DEFAULT_PLAYER_PATH}"

    def check_for_updates(self) -> UpdateCheckResult:
        from app.config.constants import APP_VERSION

        return self.update_service.check_for_updates(APP_VERSION)

    def get_bootstrap_summary(self) -> dict[str, object]:
        return {
            "settings": self.get_settings(),
            "auth_loaded": self.get_auth_state().is_authenticated,
            "clip_count": len(self.list_clips()),
            "player_url": self.get_player_url(),
            "database_path": str(self.database.db_path),
        }

    def ensure_monitoring_for_authenticated(self) -> bool:
        if self.monitor_service.get_status().is_running:
            return True

        auth_state = self.get_auth_state()
        if not auth_state.is_authenticated and not auth_state.access_token:
            return False

        def try_start(state: AuthState) -> bool:
            if not state.user_id:
                return False
            try:
                self.monitor_service.start(
                    auth_state_provider=self.get_auth_state_for_twitch_api,
                    broadcaster_id=state.user_id,
                    force_refresh_auth_state=lambda: self.get_auth_state_for_twitch_api(
                        force_refresh=True
                    ),
                )
                return True
            except Exception:
                # Keep UI usable even if auto-start fails; user can start manually.
                return False

        # Prefer fast path with persisted broadcaster id to avoid failing closed on transient
        # validation/network issues during startup.
        if try_start(auth_state):
            return True

        if auth_state.access_token and (not auth_state.is_authenticated or not auth_state.user_id):
            try:
                # Rebuild auth flags/user_id from token when persisted state is incomplete.
                auth_state = self.validate_authentication()
            except Exception:
                return False

        return try_start(auth_state)
