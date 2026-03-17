from __future__ import annotations

import sqlite3

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
    auto_start_state = {"attempted": False}
    refresh_guard = {
        "in_progress": False,
        "pending": False,
    }
    view_state = {
        "clips": [],
        "selected_clip_id": None,
        "monitor_running": False,
        "clips_render_signature": None,
        "selected_clip_id_rendered": None,
        "monitor_running_rendered": None,
    }

    def build_clips_signature(clips) -> tuple:
        return tuple(
            (
                clip.clip_id,
                clip.title,
                clip.creator_name,
                clip.thumbnail_url,
                clip.created_at.isoformat(),
                clip.is_played,
            )
            for clip in clips
        )

    def apply_selected_card_style(clip_id: str | None) -> None:
        if not clip_id:
            return
        ui.run_javascript(
            f"""
            document.querySelectorAll('.clip-card').forEach((el) => {{
              el.classList.remove('clip-card-selected', 'bg-blue-50', 'border-blue-300');
            }});
            const target = document.getElementById('clip-card-{clip_id}');
            if (target) {{
              target.classList.add('clip-card-selected', 'bg-blue-50', 'border-blue-300');
            }}
            """
        )

    def request_refresh() -> None:
        ui.timer(0.01, refresh_view, once=True)

    def select_clip(clip_id: str) -> None:
        try:
            controller.select_clip(clip_id)
            view_state["selected_clip_id"] = clip_id
            view_state["selected_clip_id_rendered"] = clip_id
            apply_selected_card_style(clip_id)
            selected = controller.get_selected_clip()
            ui.notify(f"選択中: {selected.title if selected else clip_id}")
        except Exception as error:
            ui.notify(str(error), color="negative")

    def start_monitor() -> None:
        try:
            controller.start_monitoring()
            ui.notify("監視を開始しました。")
            request_refresh()
        except Exception as error:
            ui.notify(str(error), color="negative")

    def stop_monitor() -> None:
        try:
            controller.stop_monitoring()
            ui.notify("監視を停止しました。")
            request_refresh()
        except Exception as error:
            ui.notify(str(error), color="negative")

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
            request_refresh()
        except Exception as error:
            ui.notify(str(error), color="negative")

    def delete_clip(clip_id: str) -> None:
        try:
            deleted = controller.delete_clip(clip_id)
            if deleted:
                ui.notify("クリップを削除しました。", color="primary")
                request_refresh()
            else:
                ui.notify("削除対象のクリップが見つかりませんでした。", color="warning")
        except Exception as error:
            ui.notify(str(error), color="negative")

    @ui.refreshable
    def clip_list_content() -> None:
        render_clip_table(
            view_state["clips"],
            view_state["selected_clip_id"],
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

    def _refresh_view_impl() -> None:
        monitor_status = controller.get_monitor_status()
        if not auto_start_state["attempted"]:
            auto_start_state["attempted"] = True
            auth_state = controller.get_auth_state()
            if auth_state.is_authenticated and auth_state.user_id and not monitor_status.is_running:
                try:
                    controller.start_monitoring(auth_state.user_id)
                    monitor_status = controller.get_monitor_status()
                except Exception:
                    pass

        clips = controller.list_clips()
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
        view_state["selected_clip_id"] = controller.get_selected_clip_id()
        view_state["monitor_running"] = monitor_status.is_running

        clips_signature = build_clips_signature(view_state["clips"])
        clips_changed = (
            view_state["clips_render_signature"] != clips_signature
        )
        monitor_changed = view_state["monitor_running_rendered"] != view_state["monitor_running"]

        if clips_changed:
            clip_list_content.refresh()
            view_state["clips_render_signature"] = clips_signature
            view_state["selected_clip_id_rendered"] = view_state["selected_clip_id"]

        if monitor_changed:
            monitor_footer.refresh()
            view_state["monitor_running_rendered"] = view_state["monitor_running"]

    def refresh_view() -> None:
        if refresh_guard["in_progress"]:
            refresh_guard["pending"] = True
            return

        refresh_guard["in_progress"] = True
        try:
            _refresh_view_impl()
        except sqlite3.OperationalError as error:
            ui.notify(f"DBアクセスエラー: {error}", color="warning")
        except Exception as error:
            print(f"[main_page.refresh_view] {error}")
        finally:
            refresh_guard["in_progress"] = False
            if refresh_guard["pending"]:
                refresh_guard["pending"] = False
                request_refresh()

    with ui.column().classes("w-full h-full gap-0"):
        with ui.column().classes("w-full flex-1 overflow-y-auto px-4 pt-0 pb-4 gap-4 main-scroll-area"):
            clip_list_content()

        with ui.row().classes("main-monitor-footer w-full shrink-0 p-3 border-t"):
            monitor_footer()

    request_refresh()
    # Polling runs in a background thread; refresh the panel periodically
    # so newly fetched clips appear without pressing Refresh.
    ui.timer(5.0, request_refresh)
