from __future__ import annotations

import webbrowser

from nicegui import ui

from app.models.update import UpdateCheckResult


def open_external_url(url: str) -> None:
    try:
        webbrowser.open(url)
    except Exception:
        ui.notify("ブラウザを開けませんでした。", color="warning")


def show_update_available_dialog(result: UpdateCheckResult) -> None:
    title = f"新しいバージョン {result.latest_version} があります。"
    ui.notify(title, color="primary")

    with ui.dialog() as dialog, ui.card().classes("w-80"):
        ui.label("アップデートがあります").classes("text-lg font-medium")
        with ui.row().classes("w-full gap-0"):
            ui.label(f"現在:{result.current_version}").classes("text-sm text-gray-700")
            ui.label(f"→").classes("text-sm text-gray-700 mx-1")
            ui.label(f"最新:{result.latest_version}").classes("text-sm text-gray-700")
            if result.release_notes_url:
                ui.button(
                    "リリースノート",
                    on_click=lambda url=result.release_notes_url: open_external_url(url),
                ).props('flat dense padding="2px 2px 0"').classes('leading-none ml-1')
        if result.message:
            ui.label(result.message).classes("text-sm text-gray-700")
            
        ui.button(
            "ダウンロード",
            on_click=lambda url=result.download_url: open_external_url(url),
        ).props("color=primary").classes("w-full")
        with ui.row().classes("w-full justify-center gap-2"):
            ui.button("閉じる", on_click=dialog.close).props("flat")
    dialog.open()
