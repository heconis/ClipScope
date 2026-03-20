from __future__ import annotations

import webbrowser
from collections.abc import Callable

from nicegui import ui

from app.application.app_controller import AppController
from app.twitch.auth_client import TwitchAuthError


def render_setup_panel(
    controller: AppController,
    open_main_tab: Callable[[], None] | None = None,
) -> None:
    auto_check_state = {"in_progress": False, "last_error": None}

    def start_monitoring_after_auth() -> None:
        status = controller.get_monitor_status()
        if status.is_running:
            return
        try:
            controller.start_monitoring()
            ui.notify("認証完了。監視を自動開始しました。", color="primary")
        except Exception as error:
            ui.notify(
                f"認証は完了しましたが、監視の自動開始に失敗しました: {error}",
                color="warning",
            )

    def classify_auth_error(message: str) -> tuple[str, str]:
        lower_message = message.lower()
        if "authorization_pending" in lower_message:
            return "warning", "ブラウザ側の承認待ちです。承認後に自動反映されます。"
        if "slow_down" in lower_message:
            return "warning", "確認が早すぎます。少し待ってから再確認してください。"
        if "expired_token" in lower_message:
            return "negative", "認証コードの有効期限が切れました。もう一度認証を開始してください。"
        if "access_denied" in lower_message:
            return "negative", "ブラウザ側で認証が拒否されました。必要なら再度認証を開始してください。"
        return "negative", message

    @ui.refreshable
    def auth_panel() -> None:
        auth_state = controller.get_auth_state()
        session = controller.get_pending_auth_session()
        player_url = controller.get_player_url()

        with ui.column().classes("w-full px-4 pt-0 pb-4 gap-4"):
            ui.label(
                "最初にTwitch認証を完了してください。"
            ).classes("text-sm text-gray-700")

            with ui.card().classes("w-full"):
                if auth_state.is_authenticated and session is None:
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label("認証を確認").classes("text-lg font-medium")
                        ui.label("認証済").classes("text-sm font-medium text-green-700")
                    ui.label("現在のトークン状態を確認します。").classes("text-sm text-gray-700")

                    def validate_auth() -> None:
                        checked = controller.validate_authentication()
                        auth_panel.refresh()
                        if checked.is_authenticated:
                            ui.notify("認証状態は有効です。", color="primary")
                        else:
                            ui.notify("認証が無効です。再認証してください。", color="warning")

                    ui.button("認証を確認", on_click=validate_auth).props("color=primary")
                else:
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label("Twitch認証を開始").classes("text-lg font-medium")
                        ui.label("未認証").classes("text-sm font-medium text-red-700")

                    def start_auth() -> None:
                        try:
                            issued = controller.start_authentication()
                            opened = webbrowser.open(issued.verification_uri)
                            if opened:
                                ui.notify("Twitch側で承認してください。", color="primary")
                            else:
                                ui.notify("下のURLから承認してください。", color="primary")
                            auth_panel.refresh()
                        except TwitchAuthError as error:
                            ui.notify(str(error), color="negative")

                    label = "Twitch認証を再開始" if session is not None else "Twitch認証を開始"
                    ui.button(label, on_click=start_auth).props("color=primary")

            with ui.card().classes("w-full"):
                ui.label("デバイス認証（ブラウザ）").classes("text-lg font-medium")
                if session is None:
                    ui.label("「Twitch認証を開始」を押してください。").classes("text-sm text-gray-600")
                else:
                    ui.link(session.verification_uri, session.verification_uri, new_tab=True).classes(
                        "text-sm"
                    )
                    ui.label(
                        "URLを開いて承認してください。"
                    ).classes("text-sm text-gray-700")

            with ui.card().classes("w-full"):
                ui.label("OBS連携").classes("text-lg font-medium")
                ui.label("ブラウザソースにURLを設定してください。").classes("text-sm text-gray-700")
                with ui.row().classes("w-full items-center gap-2"):
                    url_input = ui.input(value=player_url).props("readonly dense").classes("flex-1")
                    ui.button(
                        icon="content_copy",
                        on_click=lambda text=player_url: (
                            ui.clipboard.write(text),
                            ui.notify("URLをコピーしました。", color="primary"),
                        ),
                    ).props("flat round dense")
                url_input.classes("text-sm")

    auth_panel()

    def auto_check_auth() -> None:
        if auto_check_state["in_progress"]:
            return

        session = controller.get_pending_auth_session()
        auth_state = controller.get_auth_state()
        if session is None or auth_state.is_authenticated:
            return

        auto_check_state["in_progress"] = True
        try:
            updated = controller.complete_authentication()
            if updated.is_authenticated:
                ui.notify("認証が完了しました。", color="primary")
                start_monitoring_after_auth()
                auth_panel.refresh()
        except Exception as error:
            message = str(error)
            level, friendly = classify_auth_error(message)
            if level == "warning":
                return
            if auto_check_state["last_error"] != message:
                auto_check_state["last_error"] = message
                ui.notify(friendly, color=level)
        finally:
            auto_check_state["in_progress"] = False

    ui.timer(3.0, auto_check_auth)
