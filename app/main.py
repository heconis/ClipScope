from __future__ import annotations

import argparse
import logging
import socket
import sys

from app.application.app_controller import AppController
from app.application.auth_service import AuthService
from app.application.monitor_service import MonitorService
from app.application.settings_service import SettingsService
from app.application.update_service import UpdateService
from app.clips.clip_repository_service import ClipRepositoryService
from app.clips.selection_service import SelectionService
from app.player.server import PlayerServer
from app.storage.auth_repository import AuthRepository
from app.storage.clips_repository import ClipsRepository
from app.storage.database import Database
from app.storage.playback_repository import PlaybackRepository
from app.storage.settings_repository import SettingsRepository
from app.twitch.api_client import TwitchApiClient
from app.twitch.auth_client import TwitchAuthClient
from app.twitch.clips_service import TwitchClipsService
from app.twitch.user_service import TwitchUserService


class _UvicornShutdownNoiseFilter(logging.Filter):
    """Filter out known harmless shutdown race tracebacks from uvicorn/wsproto."""

    @staticmethod
    def _is_known_noise(message: str) -> bool:
        return (
            "CloseConnection(code=1012" in message
            and "ConnectionState.CLOSED" in message
        ) or ("asyncio.exceptions.CancelledError" in message and "starlette" in message)

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage() or ""
        if self._is_known_noise(message):
            return False
        if record.exc_info:
            error_text = str(record.exc_info[1])
            if self._is_known_noise(error_text):
                return False
        return True


def _install_shutdown_noise_filter() -> None:
    logger = logging.getLogger("uvicorn.error")
    shutdown_filter = _UvicornShutdownNoiseFilter()
    logger.addFilter(shutdown_filter)
    for handler in logger.handlers:
        handler.addFilter(shutdown_filter)


def build_controller() -> AppController:
    database = Database()
    database.initialize()

    settings_repository = SettingsRepository(database)
    settings_service = SettingsService(settings_repository)
    auth_repository = AuthRepository(database)
    auth_service = AuthService(TwitchAuthClient(), TwitchUserService(), auth_repository)
    clips_repository = ClipsRepository(database)
    playback_repository = PlaybackRepository(database)
    clip_repository_service = ClipRepositoryService(clips_repository)
    selection_service = SelectionService(clips_repository, playback_repository)
    api_client = TwitchApiClient()
    clips_service = TwitchClipsService(api_client)
    monitor_service = MonitorService(clips_service, clip_repository_service)
    update_service = UpdateService()
    settings = settings_service.load()
    player_server = PlayerServer("127.0.0.1", settings.local_server_port, selection_service)

    controller = AppController(
        settings_service=settings_service,
        auth_service=auth_service,
        auth_repository=auth_repository,
        clip_repository_service=clip_repository_service,
        selection_service=selection_service,
        monitor_service=monitor_service,
        update_service=update_service,
        player_server=player_server,
        database=database,
    )
    return controller


def print_summary(controller: AppController) -> None:
    summary = controller.get_bootstrap_summary()
    settings = summary["settings"]
    print("ClipScope bootstrap is ready.")
    print(
        "Settings: "
        f"polling={settings.polling_interval_seconds}s, "
        f"port={settings.local_server_port}, "
        f"max_clips={settings.max_clip_count}, "
        f"retention_days={settings.retention_days}"
    )
    print(f"Auth loaded: {summary['auth_loaded']}")
    print(f"Clip count: {summary['clip_count']}")
    print(f"Player URL: {summary['player_url']}")
    print(f"Database path: {summary['database_path']}")
    print(f"Twitch auth configured: {TwitchAuthClient().is_configured()}")
    print(f"Twitch API configured: {TwitchApiClient().is_configured()}")
    print(f"Twitch user service configured: {TwitchUserService().is_configured()}")


def run_ui(controller: AppController) -> None:
    from nicegui import app, ui

    from app.gui.app_ui import register_ui

    _install_shutdown_noise_filter()
    register_ui(controller)
    settings = controller.get_settings()
    app.native.window_args.update(
        resizable=False,
        min_size=(360, 640),
        on_top=settings.always_on_top,
    )
    ui_port = find_available_port(8080)
    try:
        ui.run(
            title="ClipScope",
            reload=False,
            native=True,
            frameless=True,
            host="127.0.0.1",
            port=ui_port,
            window_size=(360, 640),
        )
    except Exception as error:
        # Harmless shutdown race in uvicorn/wsproto when the native window closes first.
        # Treat it as a normal exit to avoid noisy tracebacks.
        message = str(error)
        if "CloseConnection(code=1012" in message and "ConnectionState.CLOSED" in message:
            return
        raise


def find_available_port(start_port: int) -> int:
    port = start_port
    while port < start_port + 50:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    raise RuntimeError("No available UI port found.")


def main() -> None:
    parser = argparse.ArgumentParser(description="ClipScope bootstrap")
    parser.add_argument("--run-ui", action="store_true", help="Start the NiceGUI application.")
    if getattr(sys, "frozen", False):
        # In windowed frozen apps, unknown launcher args can be injected and
        # stderr may be unavailable for argparse error printing.
        args, _unknown = parser.parse_known_args()
        if not args.run_ui:
            args.run_ui = True
    else:
        args = parser.parse_args()

    controller = build_controller()
    controller.bootstrap()
    try:
        if args.run_ui:
            run_ui(controller)
        else:
            print_summary(controller)
    finally:
        controller.shutdown()


if __name__ == "__main__":
    main()
