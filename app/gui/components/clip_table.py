from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from nicegui import ui

from app.models.clip import ClipItem

JST = timezone(timedelta(hours=9), name="JST")


def _to_jst_text(dt: datetime) -> str:
    return dt.astimezone(JST).strftime("%Y-%m-%d %H:%M:%S")


def render_clip_table(
    clips: list[ClipItem],
    selected_clip_id: str | None,
    on_select: Callable[[str], None],
    on_refresh: Callable[[], None] | None = None,
    on_delete: Callable[[str], None] | None = None,
) -> None:
    with ui.column().classes("w-full gap-2"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(f"クリップ一覧（{len(clips)}件）").classes("text-xl font-semibold")
            if on_refresh is not None:
                ui.button(icon="refresh", on_click=on_refresh).props("flat round dense")

        if not clips:
            ui.label("読み込み済みクリップはありません。").classes("text-sm text-gray-600")
            return

        for clip in clips:
            is_selected = clip.clip_id == selected_clip_id
            card_classes = "clip-card w-full cursor-pointer border rounded px-2 py-0 shadow-sm transition-colors"
            if is_selected:
                card_classes += " clip-card-selected bg-blue-50 border-blue-300"
            else:
                card_classes += " clip-card-default"

            with (
                ui.card()
                .classes(card_classes)
                .props(f"id=clip-card-{clip.clip_id}")
                .on("click", lambda _=None, clip_id=clip.clip_id: on_select(clip_id))
            ):
                status_text = "再生済" if clip.is_played else "未再生"
                status_class = "text-xs font-medium text-green-700" if clip.is_played else "text-xs font-medium text-amber-700"

                with ui.row().classes("w-full items-center gap-2"):
                    with ui.row().classes("items-center gap-2 min-w-0 flex-1"):
                        ui.label(status_text).classes(status_class)
                        ui.label(f"作成者: {clip.creator_name}").classes("text-xs text-gray-600 truncate")
                    if on_delete is not None:
                        delete_button = ui.button(icon="delete_outline").props("flat round dense color=negative")
                        delete_button.classes("ml-auto -mr-2.5")
                        delete_button.on("click.stop", lambda _=None, clip_id=clip.clip_id: on_delete(clip_id))

                with ui.row().classes("w-full items-start gap-2 -mt-4"):
                    if clip.thumbnail_url:
                        ui.image(clip.thumbnail_url).classes("w-20 h-12 rounded object-cover bg-black shrink-0")
                    else:
                        ui.element("div").classes("w-20 h-12 rounded bg-black shrink-0")

                    title_text = clip.title or "(無題)"
                    ui.label(title_text).classes(
                        "text-base font-medium leading-snug truncate min-w-0 flex-1"
                    ).tooltip(title_text)

                with ui.row().classes("w-full justify-end -mt-10"):
                    ui.label(f"{round(clip.duration_seconds)}秒").classes("text-xs text-gray-500")

                with ui.row().classes("w-full justify-end -mt-5"):
                    ui.label(_to_jst_text(clip.created_at)).classes("text-xs text-gray-500")
