from __future__ import annotations

import sys

from nicegui import app, run, ui
from starlette.responses import PlainTextResponse

from app.application.app_controller import AppController
from app.gui.main_page import render_main_panel
from app.gui.settings_page import render_settings_panel
from app.gui.setup_page import render_setup_panel
from app.gui.update_ui import show_update_available_dialog


def _close_pyinstaller_splash() -> None:
    if not getattr(sys, "frozen", False):
        return
    try:
        import pyi_splash  # type: ignore
    except Exception:
        return
    try:
        pyi_splash.close()
    except Exception:
        # Ignore if already closed or unavailable in current runtime.
        return


def register_ui(controller: AppController) -> None:
    @app.exception_handler(404)
    async def _handle_not_found(_request, _exc) -> PlainTextResponse:
        # In frozen (PyInstaller) mode, NiceGUI's default 404 handler may try to
        # execute the .exe as a Python script. Force a plain 404 response.
        return PlainTextResponse("Not Found", status_code=404)

    @ui.page("/")
    def _index_page() -> None:
        settings = controller.get_settings()
        ui.colors(primary="#2563eb", secondary="#0f172a", accent="#f59e0b")
        dark_mode = ui.dark_mode(value=(settings.theme_mode == "dark"))
        ui.add_css(
            """
            html, body, #q-app {
              width: 100%;
              height: 100%;
              margin: 0;
              padding: 0;
              overflow: hidden;
            }
            .nicegui-content {
              width: 100%;
              height: 100%;
              margin: 0 !important;
              padding: 0 !important;
              gap: 0 !important;
            }
            #q-app > .nicegui-content {
              margin: 0 !important;
              padding: 0 !important;
            }
            .body--dark .bg-white {
              background-color: #1d1d1d !important;
            }
            .body--dark .text-gray-500,
            .body--dark .text-gray-600,
            .body--dark .text-gray-700 {
              color: #cbd5e1 !important;
            }
            .body--dark .border {
              border-color: #475569 !important;
            }
            .body--dark .q-card {
              box-shadow: 0 2px 8px rgba(0, 0, 0, 0.55) !important;
            }
            .clip-card-default.q-card {
              background-color: #ffffff;
              border-color: #e5e7eb;
            }
            .body--dark .clip-card.q-card {
              background-color: #1d1d1d !important;
              border-color: #475569 !important;
            }
            .body--dark .clip-card.clip-card-selected.q-card {
              background-color: #0f172a !important;
              border-color: #3b82f6 !important;
            }
            .main-monitor-footer {
              background-color: #ffffff;
              border-color: #e5e7eb;
            }
            .body--dark .main-monitor-footer {
              background-color: inherit !important;
              border-color: #374151 !important;
            }
            .settings-section {
              background-color: #ffffff;
              border-color: #e5e7eb;
            }
            .settings-card {
              background-color: #ffffff;
              border-color: #e5e7eb;
            }
            .settings-footer {
              background-color: #ffffff;
              border-color: #e5e7eb;
            }
            .body--dark .settings-section {
              background-color: #1d1d1d !important;
              border-color: #475569 !important;
            }
            .body--dark .settings-card {
              background-color: #1d1d1d !important;
              border-color: #475569 !important;
            }
            .body--dark .settings-footer {
              background-color: inherit !important;
              border-color: #374151 !important;
            }
            """
        )

        auth_state = controller.get_auth_state()
        auto_window_flag_bootstrap = {"done": False}
        splash_state = {"closed": False}
        startup_update_state = {"started": False}

        with ui.column().classes("w-screen h-screen gap-0"):
            with ui.row().classes("w-full items-center justify-between pl-4 pr-1 py-0 bg-[#468ace] text-white shrink-0"):
                ui.label("ClipScope").classes("text-xl font-bold")
                ui.button(icon="close", on_click=app.shutdown).props(
                    "flat round dense color=white size=lg"
                ).classes("mr-0")

            with ui.column().classes("w-full flex-1 overflow-y-auto overflow-x-hidden gap-0 app-scroll-area"):
                with ui.tabs().classes("w-full") as tabs:
                    setup_tab = ui.tab("セットアップ").classes("flex-1 justify-center")
                    main_tab = ui.tab("メイン").classes("flex-1 justify-center")
                    settings_tab = ui.tab("設定").classes("flex-1 justify-center")

                tabs.value = main_tab if auth_state.is_authenticated else setup_tab

                def open_main_tab() -> None:
                    tabs.value = main_tab

                def apply_theme_mode(mode: str) -> None:
                    if mode == "dark":
                        dark_mode.enable()
                    else:
                        dark_mode.disable()

                with ui.tab_panels(tabs, value=tabs.value).classes("w-full h-full bg-transparent"):
                    with ui.tab_panel(setup_tab).classes("h-full"):
                        render_setup_panel(controller, open_main_tab=open_main_tab)
                    with ui.tab_panel(main_tab).classes("h-full"):
                        render_main_panel(controller)
                    with ui.tab_panel(settings_tab).classes("h-full"):
                        render_settings_panel(controller, on_theme_change=apply_theme_mode)

        def ensure_window_flags_on_ui_ready() -> None:
            if not app.native.main_window:
                return
            if not auto_window_flag_bootstrap["done"]:
                try:
                    app.native.main_window.set_always_on_top(
                        bool(controller.get_settings().always_on_top)
                    )
                except Exception:
                    pass
                auto_window_flag_bootstrap["done"] = True
            if not splash_state["closed"]:
                _close_pyinstaller_splash()
                splash_state["closed"] = True

        async def check_updates_on_startup() -> None:
            if startup_update_state["started"]:
                return
            startup_update_state["started"] = True

            try:
                current_settings = controller.get_settings()
                if not current_settings.auto_update_check:
                    return
                result = await run.io_bound(controller.check_for_updates)
            except Exception:
                return

            if result.is_update_available:
                show_update_available_dialog(result)

        ui.timer(0.2, ensure_window_flags_on_ui_ready)
        ui.timer(1.0, check_updates_on_startup, once=True)
