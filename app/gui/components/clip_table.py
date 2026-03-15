from __future__ import annotations

from nicegui import ui

from app.models.clip import ClipItem


def render_clip_table(
    clips: list[ClipItem],
    selected_clip_id: str | None,
    on_select: callable,
    on_refresh: callable | None = None,
    on_delete: callable | None = None,
) -> None:
    with ui.column().classes("w-full gap-2"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(f"クリップ一覧（{len(clips)}件）").classes("text-lg font-medium")
            if on_refresh is not None:
                ui.button(icon="refresh", on_click=on_refresh).props("flat round dense")
        if not clips:
            ui.label("取得済みクリップはありません。").classes("text-sm text-gray-600")
            return

        for clip in clips:
            is_selected = clip.clip_id == selected_clip_id
            card_classes = "w-full cursor-pointer border rounded px-2.5 py-1.5 shadow-sm transition-colors"
            if is_selected:
                card_classes += " bg-blue-50 border-blue-300"
            else:
                card_classes += " bg-white"
            with ui.card().classes(card_classes).on(
                "click", lambda _=None, clip_id=clip.clip_id: on_select(clip_id)
            ):
                with ui.row().classes("w-full items-start justify-between gap-1"):
                    ui.label(clip.title or "（無題）").classes("text-sm font-medium break-words leading-none pt-2.5")
                    with ui.row().classes("items-center gap-1"):
                        status_text = "再生済" if clip.is_played else "未再生"
                        status_class = "text-xs text-green-700" if clip.is_played else "text-xs text-amber-700"
                        ui.label(status_text).classes(status_class)
                        if on_delete is not None:
                            delete_button = ui.button(icon="delete_outline").props("flat round dense color=negative")
                            delete_button.on("click.stop", lambda _=None, clip_id=clip.clip_id: on_delete(clip_id))
                with ui.row().classes("w-full justify-between gap-2 -mt-3"):
                    ui.label(f"作成者: {clip.creator_name}").classes("text-xs text-gray-600")
                    ui.label(clip.created_at.strftime("%Y-%m-%d %H:%M:%S")).classes(
                        "text-[11px] text-gray-500"
                    )
