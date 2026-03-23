from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.clips.clip_repository_service import ClipRepositoryService
from app.models.auth import AuthState
from app.models.clip import ClipItem
from app.twitch.api_client import TwitchApiError
from app.twitch.clips_service import TwitchClipsService


@dataclass(slots=True)
class MonitorStatus:
    is_running: bool = False
    monitoring_started_at: datetime | None = None
    last_run_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None


class MonitorService:
    _STARTED_AT_SAFETY_MARGIN_SECONDS = 2

    def __init__(
        self,
        clips_service: TwitchClipsService,
        clip_repository_service: ClipRepositoryService,
        polling_interval_seconds: int = 10,
    ) -> None:
        self.clips_service = clips_service
        self.clip_repository_service = clip_repository_service
        self.polling_interval_seconds = polling_interval_seconds
        self._status = MonitorStatus()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def get_status(self) -> MonitorStatus:
        return self._status

    def configure(self, polling_interval_seconds: int) -> None:
        self.polling_interval_seconds = polling_interval_seconds

    def start(
        self,
        auth_state_provider: Callable[[], AuthState],
        broadcaster_id: str,
        first: int = 20,
        force_refresh_auth_state: Callable[[], AuthState] | None = None,
    ) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._status.is_running = True
        self._status.monitoring_started_at = datetime.now(timezone.utc)
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(auth_state_provider, broadcaster_id, first, force_refresh_auth_state),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._status.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def run_once(
        self,
        auth_state: AuthState,
        broadcaster_id: str,
        first: int = 20,
        force_refresh_auth_state: Callable[[], AuthState] | None = None,
    ) -> list[ClipItem]:
        self._status.last_run_at = datetime.now(timezone.utc)
        if not auth_state.access_token:
            self._status.last_error = "Missing access token."
            return []
        try:
            return self._fetch_and_merge(auth_state, broadcaster_id, first)
        except TwitchApiError as exc:
            if exc.status_code == 401 and force_refresh_auth_state is not None:
                refreshed_auth = force_refresh_auth_state()
                if refreshed_auth.access_token:
                    try:
                        return self._fetch_and_merge(refreshed_auth, broadcaster_id, first)
                    except Exception as retry_exc:
                        self._status.last_error = str(retry_exc)
                        return []
            self._status.last_error = str(exc)
            return []
        except Exception as exc:
            self._status.last_error = str(exc)
            return []

    def _run_loop(
        self,
        auth_state_provider: Callable[[], AuthState],
        broadcaster_id: str,
        first: int,
        force_refresh_auth_state: Callable[[], AuthState] | None,
    ) -> None:
        while not self._stop_event.is_set():
            self.run_once(
                auth_state_provider(),
                broadcaster_id,
                first=first,
                force_refresh_auth_state=force_refresh_auth_state,
            )
            if self._stop_event.wait(self.polling_interval_seconds):
                break
        self._status.is_running = False

    def _resolve_started_at(self) -> datetime:
        base_started_at = self._status.monitoring_started_at or self._status.last_success_at or self._status.last_run_at
        if base_started_at is None:
            base_started_at = datetime.now(timezone.utc)

        latest_created_at = self.clip_repository_service.latest_clip_created_at()
        if latest_created_at is None:
            return base_started_at

        safety_margin = timedelta(seconds=self._STARTED_AT_SAFETY_MARGIN_SECONDS)
        candidate = latest_created_at - safety_margin
        return max(base_started_at, candidate)

    def _fetch_and_merge(self, auth_state: AuthState, broadcaster_id: str, first: int) -> list[ClipItem]:
        window_started_at = self._resolve_started_at()
        clips = self.clips_service.get_clips_for_broadcaster(
            access_token=auth_state.access_token,
            broadcaster_id=broadcaster_id,
            started_at=window_started_at,
            first=first,
        )
        managed = self.clip_repository_service.merge_clips(clips)
        self._status.last_success_at = datetime.now(timezone.utc)
        self._status.last_error = None
        return managed
