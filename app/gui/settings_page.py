from __future__ import annotations

from nicegui import ui

from app.application.app_controller import AppController


def render_settings_panel(controller: AppController) -> None:
    settings = controller.get_settings().copy()

    with ui.column().classes("w-full p-4 gap-4"):
        ui.label("動作設定を変更できます。").classes("text-sm text-gray-700")

        def render_number_row(
            label: str,
            hint: str,
            value: int,
            minimum: int,
            maximum: int,
        ) -> ui.number:
            with ui.card().classes("w-full px-3 py-2"):
                ui.label(label).classes("text-sm font-medium leading-tight")
                ui.label(hint).classes("text-[11px] text-gray-600 leading-tight")
                field = (
                    ui.number(value=value, min=minimum, max=maximum, step=1)
                    .props("dense outlined inputmode=numeric")
                    .classes("w-full")
                )
            return field

        clip_limit = render_number_row(
            "保持最大クリップ件数",
            "保持するクリップの上限件数です。（1〜1000件）",
            settings.max_clip_count,
            1,
            1000,
        )
        retention = render_number_row(
            "保持日数",
            "この日数を超えると除外されます。（1〜365日）",
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

        def save_settings() -> None:
            defaults = controller.get_default_settings()
            settings.polling_interval_seconds = int(float(polling.value or defaults.polling_interval_seconds))
            settings.local_server_port = int(float(port.value or defaults.local_server_port))
            settings.max_clip_count = int(float(clip_limit.value or defaults.max_clip_count))
            settings.retention_days = int(float(retention.value or defaults.retention_days))
            saved = controller.save_settings(settings.copy())
            ui.notify(f"設定を保存しました。", color="primary")

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
                        polling.value = reset.polling_interval_seconds
                        port.value = reset.local_server_port
                        clip_limit.value = reset.max_clip_count
                        retention.value = reset.retention_days
                        dialog.close()
                        ui.notify("設定を初期値に戻しました。", color="primary")

                    ui.button("すべて初期化", on_click=do_reset).props("color=negative")

            dialog.open()

        ui.button("保存", on_click=save_settings).props("color=primary").classes("w-full")
        ui.button("すべて初期化", on_click=reset_settings).props("outline color=negative").classes("w-full")
