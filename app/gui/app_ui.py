from __future__ import annotations

from nicegui import app, ui
from starlette.responses import PlainTextResponse

from app.application.app_controller import AppController
from app.gui.main_page import render_main_panel
from app.gui.settings_page import render_settings_panel
from app.gui.setup_page import render_setup_panel


def register_ui(controller: AppController) -> None:
    @app.exception_handler(404)
    async def _handle_not_found(_request, _exc) -> PlainTextResponse:
        # In frozen (PyInstaller) mode, NiceGUI's default 404 handler may try to
        # execute the .exe as a Python script. Force a plain 404 response.
        return PlainTextResponse("Not Found", status_code=404)

    @ui.page("/")
    def _index_page() -> None:
        ui.colors(primary="#2563eb", secondary="#0f172a", accent="#f59e0b")
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
            """
        )

        auth_state = controller.get_auth_state()
        auto_monitor_bootstrap = {"done": False}
        auto_window_flag_bootstrap = {"done": False}

        with ui.column().classes("w-screen h-screen gap-0"):
            with ui.row().classes("w-full items-center justify-between pl-4 pr-1 py-3 bg-primary text-white shrink-0"):
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

                with ui.tab_panels(tabs, value=tabs.value).classes("w-full h-full bg-transparent"):
                    with ui.tab_panel(setup_tab).classes("h-full"):
                        render_setup_panel(controller, open_main_tab=open_main_tab)
                    with ui.tab_panel(main_tab).classes("h-full"):
                        render_main_panel(controller)
                    with ui.tab_panel(settings_tab).classes("h-full"):
                        render_settings_panel(controller)

        def ensure_monitor_on_ui_ready() -> None:
            if auto_monitor_bootstrap["done"]:
                return
            auto_monitor_bootstrap["done"] = True
            state = controller.get_auth_state()
            if state.is_authenticated:
                controller.ensure_monitoring_for_authenticated()

        ui.timer(1.0, ensure_monitor_on_ui_ready)

        def ensure_window_flags_on_ui_ready() -> None:
            if auto_window_flag_bootstrap["done"]:
                return
            if not app.native.main_window:
                return
            try:
                app.native.main_window.set_always_on_top(
                    bool(controller.get_settings().always_on_top)
                )
            except Exception:
                return
            auto_window_flag_bootstrap["done"] = True

        ui.timer(1.0, ensure_window_flags_on_ui_ready)
