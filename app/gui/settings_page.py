from __future__ import annotations

from collections.abc import Callable

from nicegui import app, run, ui

from app.application.app_controller import AppController
from app.config.constants import (
    AUTHOR_BOOTH_URL,
    AUTHOR_NAME,
    AUTHOR_TWITCH_URL,
    AUTHOR_WEBSITE_URL,
    AUTHOR_X_URL,
    AUTHOR_YOUTUBE_URL,
    KOFI_SUPPORT_URL,
)
from app.gui.update_ui import open_external_url, show_update_available_dialog


def render_settings_panel(
    controller: AppController,
    on_theme_change: Callable[[str], None] | None = None,
) -> None:
    settings = controller.get_settings().copy()
    valid_themes = {"light", "dark"}
    settings.theme_mode = str(settings.theme_mode or "light")
    if settings.theme_mode not in valid_themes:
        settings.theme_mode = "light"

    author_links = [
        ("ホームページ", AUTHOR_WEBSITE_URL, "/app-assets/icons/website.png"),
        ("X", AUTHOR_X_URL, "/app-assets/icons/x.png"),
        ("Twitch", AUTHOR_TWITCH_URL, "/app-assets/icons/twitch.png"),
        ("YouTube", AUTHOR_YOUTUBE_URL, "/app-assets/icons/youtube.png"),
        ("BOOTH", AUTHOR_BOOTH_URL, "/app-assets/icons/booth.png"),
    ]

    with ui.column().classes("settings-root w-full h-full gap-0"):
        with ui.column().classes("settings-scroll w-full flex-1 overflow-y-auto px-4 pt-0 pb-4 gap-3"):
            with ui.card().classes("settings-section w-full px-3 py-3 gap-2 border"):
                with ui.row().classes("w-full gap-2 mt-2"):
                    ui.label("作者:").classes("text-sm font-medium leading-tight")
                    ui.label(AUTHOR_NAME).classes("text-sm font-semibold leading-tight")
                    for label, url, image_path in author_links:
                        with ui.button(
                            on_click=lambda _, target=url: open_external_url(target)
                        ).props("flat round dense").classes("shrink-0 -mt-2").style(
                            "padding: 0px; min-width: 0;"
                        ):
                            ui.image(image_path).classes("size-5 rounded")
                            ui.tooltip(label)

            with ui.expansion("一般", value=True).classes("settings-section w-full border rounded"):
                with ui.column().classes("w-full p-3 gap-2"):
                    with ui.card().classes("settings-card w-full px-3 py-2"):
                        with ui.row().classes("w-full items-center justify-between"):
                            ui.label("テーマ").classes("text-sm font-medium leading-tight")
                            theme_mode = (
                                ui.select(
                                    options={"light": "ライト", "dark": "ダーク"},
                                    value=settings.theme_mode,
                                )
                                .props("dense outlined")
                                .classes("w-28")
                            )

                            def on_theme_preview() -> None:
                                selected = str(theme_mode.value or "light")
                                if selected not in valid_themes:
                                    selected = "light"
                                settings.theme_mode = selected
                                apply_theme_mode()

                            theme_mode.on("update:model-value", lambda _=None: on_theme_preview())
                    
                    with ui.card().classes("settings-card w-full px-3 py-2"):
                        with ui.row().classes("w-full items-center justify-between"):
                            ui.label("常に最前面に表示").classes("text-sm font-medium leading-tight")
                            always_on_top = ui.checkbox(value=settings.always_on_top).props("dense")

                    with ui.card().classes("settings-card w-full px-3 py-2"):
                        with ui.row().classes("w-full items-center justify-between"):
                            ui.label("通知音を再生").classes("text-sm font-medium leading-tight")
                            play_sound = ui.checkbox(value=settings.play_sound_on_new_clip).props("dense")

                    with ui.card().classes("settings-card w-full px-3 py-2 gap-2"):
                        async def manual_check_updates() -> None:
                            try:
                                result = await run.io_bound(controller.check_for_updates)
                            except Exception as error:
                                ui.notify(f"更新確認に失敗しました: {error}", color="warning")
                                return

                            if result.is_update_available:
                                show_update_available_dialog(result)
                            else:
                                ui.notify("最新バージョンです。", color="positive")

                        ui.label("アップデート").classes("text-sm font-medium leading-tight")
                        with ui.row().classes("w-full items-center justify-between gap-2"):
                            ui.label("自動更新確認").classes("text-[11px] text-gray-600 leading-tight")
                            auto_update_check = ui.checkbox(value=settings.auto_update_check).props("dense")
                        ui.button("手動で確認", on_click=manual_check_updates).props(
                            'color=primary dense padding="8px 12px 6px"'
                        ).classes('leading-none w-full')

                    with ui.card().classes("settings-card w-full px-3 py-2 gap-2"):
                        ui.label("サポート").classes("text-sm font-medium leading-tight")
                        ui.label("Ko-fi の支援ページを開きます。").classes("text-[11px] text-gray-600 leading-tight")
                        ui.button(
                            "Ko-fiで支援",
                            on_click=lambda: open_external_url(KOFI_SUPPORT_URL),
                        ).style("background: #e86e67 !important; color: white !important;").classes("w-full")

            with ui.expansion("詳細", value=False).classes("settings-section w-full border rounded"):
                with ui.column().classes("w-full p-3 gap-3"):
                    def render_number_row(
                        label: str,
                        hint: str,
                        value: int,
                        minimum: int,
                        maximum: int,
                    ) -> ui.number:
                        with ui.card().classes("settings-card w-full px-3 py-2"):
                            ui.label(label).classes("text-sm font-medium leading-tight")
                            ui.label(hint).classes("text-[11px] text-gray-600 leading-tight")
                            field = (
                                ui.number(value=value, min=minimum, max=maximum, step=1)
                                .props("dense outlined inputmode=numeric")
                                .classes("w-full")
                            )
                        return field

                    clip_limit = render_number_row(
                        "クリップ最大保持件数",
                        "保持するクリップの上限件数です。（1〜1000件）",
                        settings.max_clip_count,
                        1,
                        1000,
                    )
                    retention = render_number_row(
                        "クリップ保持日数",
                        "この日数を超えると古いクリップを削除します。（1〜365日）",
                        settings.retention_days,
                        1,
                        365,
                    )
                    polling = render_number_row(
                        "ポーリング間隔（秒）",
                        "クリップを監視する間隔です。（5〜60秒）",
                        settings.polling_interval_seconds,
                        5,
                        60,
                    )
                    port = render_number_row(
                        "ローカルサーバーポート",
                        "OBSのブラウザソースが参照するポートです。（1024〜65535）",
                        settings.local_server_port,
                        1024,
                        65535,
                    )

        def apply_window_flags() -> None:
            app.native.window_args["on_top"] = bool(settings.always_on_top)
            if app.native.main_window:
                app.native.main_window.set_always_on_top(bool(settings.always_on_top))

        def apply_theme_mode() -> None:
            if on_theme_change:
                on_theme_change(settings.theme_mode)

        def save_settings() -> None:
            defaults = controller.get_default_settings()
            settings.always_on_top = bool(always_on_top.value)
            settings.play_sound_on_new_clip = bool(play_sound.value)
            settings.auto_update_check = bool(auto_update_check.value)
            settings.theme_mode = str(theme_mode.value or "light")
            if settings.theme_mode not in valid_themes:
                settings.theme_mode = "light"
            settings.polling_interval_seconds = int(float(polling.value or defaults.polling_interval_seconds))
            settings.local_server_port = int(float(port.value or defaults.local_server_port))
            settings.max_clip_count = int(float(clip_limit.value or defaults.max_clip_count))
            settings.retention_days = int(float(retention.value or defaults.retention_days))
            controller.save_settings(settings.copy())
            apply_window_flags()
            apply_theme_mode()
            ui.notify("設定を保存しました。", color="primary")

        def reset_settings() -> None:
            with ui.dialog() as dialog, ui.card():
                ui.label("すべての設定を初期値に戻しますか？")
                with ui.row().classes("justify-end gap-2"):
                    ui.button("キャンセル", on_click=dialog.close).props("flat")

                    def do_reset() -> None:
                        reset = controller.reset_settings()
                        settings.polling_interval_seconds = reset.polling_interval_seconds
                        settings.local_server_port = reset.local_server_port
                        settings.max_clip_count = reset.max_clip_count
                        settings.retention_days = reset.retention_days
                        settings.always_on_top = reset.always_on_top
                        settings.play_sound_on_new_clip = reset.play_sound_on_new_clip
                        settings.auto_update_check = reset.auto_update_check
                        settings.theme_mode = str(reset.theme_mode or "light")
                        if settings.theme_mode not in valid_themes:
                            settings.theme_mode = "light"
                        polling.value = reset.polling_interval_seconds
                        port.value = reset.local_server_port
                        clip_limit.value = reset.max_clip_count
                        retention.value = reset.retention_days
                        always_on_top.value = reset.always_on_top
                        play_sound.value = reset.play_sound_on_new_clip
                        auto_update_check.value = reset.auto_update_check
                        theme_mode.value = settings.theme_mode
                        apply_window_flags()
                        apply_theme_mode()
                        dialog.close()
                        ui.notify("設定を初期値に戻しました。", color="primary")

                    ui.button("すべて初期化", on_click=do_reset).props("color=negative")

            dialog.open()

        with ui.row().classes("settings-footer w-full shrink-0 p-3 gap-2 border-t"):
            ui.button("保存", on_click=save_settings).props("color=primary").classes("w-full")
            ui.button("すべて初期化", on_click=reset_settings).props("color=negative").classes("w-full")
