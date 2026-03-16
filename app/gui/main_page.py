from __future__ import annotations

from nicegui import ui

from app.application.app_controller import AppController
from app.gui.components.clip_table import render_clip_table
from app.gui.notification_sound import play_new_clip_sound


def render_main_panel(controller: AppController) -> None:
    clip_diff_state = {
        "initialized": False,
        "known_clip_ids": set(),
        "suppress_next_change_notice": False,
    }
    auto_start_state = {
        "enabled": True,
        "attempts": 0,
        "max_attempts": 5,
    }
    view_state = {
        "clips": [],
        "monitor_running": False,
    }

    def select_clip(clip_id: str) -> None:
        try:
            controller.select_clip(clip_id)
            selected = controller.get_selected_clip()
            ui.notify(f"選択中: {selected.title if selected else clip_id}")
            refresh_view()
        except Exception as error:
            ui.notify(str(error), color="negative")

    def start_monitor() -> None:
        try:
            auto_start_state["enabled"] = False
            controller.start_monitoring()
            ui.notify("監視を開始しました。")
            refresh_view()
        except Exception as error:
            ui.notify(str(error), color="negative")

    def stop_monitor() -> None:
        auto_start_state["enabled"] = False
        controller.stop_monitoring()
        ui.notify("監視を停止しました。")
        refresh_view()

    def refresh_clips() -> None:
        try:
            before_ids = {clip.clip_id for clip in view_state["clips"]}
            refreshed = controller.refresh_clips()
            refreshed_ids = {clip.clip_id for clip in refreshed}
            new_clip_count = len(refreshed_ids - before_ids)
            ui.notify(f"更新完了: {new_clip_count}件のクリップを読み込みました。", color="primary")
            if new_clip_count > 0 and controller.get_settings().play_sound_on_new_clip:
                play_new_clip_sound()
            clip_diff_state["suppress_next_change_notice"] = True
            refresh_view()
        except Exception as error:
            ui.notify(str(error), color="negative")

    def delete_clip(clip_id: str) -> None:
        try:
            deleted = controller.delete_clip(clip_id)
            if deleted:
                ui.notify("クリップを削除しました。", color="primary")
                refresh_view()
            else:
                ui.notify("削除対象のクリップが見つかりませんでした。", color="warning")
        except Exception as error:
            ui.notify(str(error), color="negative")

    @ui.refreshable
    def clip_list_content() -> None:
        render_clip_table(
            view_state["clips"],
            controller.get_selected_clip_id(),
            on_select=select_clip,
            on_refresh=refresh_clips,
            on_delete=delete_clip,
        )

    @ui.refreshable
    def monitor_footer() -> None:
        if view_state["monitor_running"]:
            ui.button("監視を停止", on_click=stop_monitor).props("color=negative").classes("w-full")
        else:
            ui.button("監視を開始", on_click=start_monitor).props("color=primary").classes("w-full")

    def refresh_view() -> None:
        monitor_status = controller.get_monitor_status()
        auth_state = controller.get_auth_state()
        if (
            auto_start_state["enabled"]
            and auth_state.is_authenticated
            and not monitor_status.is_running
            and auto_start_state["attempts"] < auto_start_state["max_attempts"]
        ):
            auto_start_state["attempts"] += 1
            started = controller.ensure_monitoring_for_authenticated()
            if started:
                auto_start_state["enabled"] = False
        if not auth_state.is_authenticated:
            auto_start_state["enabled"] = False

        clips = controller.list_clips()
        monitor_status = controller.get_monitor_status()
        current_clip_ids = {clip.clip_id for clip in clips}
        suppressed = bool(clip_diff_state["suppress_next_change_notice"])
        clip_diff_state["suppress_next_change_notice"] = False

        if clip_diff_state["initialized"]:
            new_clip_count = len(current_clip_ids - clip_diff_state["known_clip_ids"])
            if new_clip_count > 0 and not suppressed and monitor_status.is_running:
                ui.notify(f"更新完了: {new_clip_count}件のクリップを読み込みました。", color="primary")
                if controller.get_settings().play_sound_on_new_clip:
                    play_new_clip_sound()
        else:
            clip_diff_state["initialized"] = True

        clip_diff_state["known_clip_ids"] = current_clip_ids
        view_state["clips"] = clips
        view_state["monitor_running"] = monitor_status.is_running

        clip_list_content.refresh()
        monitor_footer.refresh()

    with ui.column().classes("w-full h-full gap-0"):
        with ui.column().classes("w-full flex-1 overflow-y-auto p-4 gap-4 main-scroll-area"):
            clip_list_content()

        with ui.row().classes("w-full shrink-0 p-3 border-t bg-white"):
            monitor_footer()

    refresh_view()
    # Polling runs in a background thread; refresh the panel periodically
    # so newly fetched clips appear without pressing Refresh.
    ui.timer(2.0, refresh_view)

