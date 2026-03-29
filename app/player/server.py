from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from app.clips.selection_service import SelectionService
from app.player.player_page import build_player_page
from app.player.state_endpoint import PlayerStateEndpoint


class PlayerServer:
    def __init__(self, host: str, port: int, selection_service: SelectionService) -> None:
        self.host = host
        self.port = port
        self.selection_service = selection_service
        self.state_endpoint = PlayerStateEndpoint(selection_service)
        self._server = self._create_server()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        thread = self._thread
        self._thread = None
        if not thread:
            return

        try:
            self._server.shutdown()
        except KeyboardInterrupt:
            # Allow app shutdown to finish quietly when OS close and Ctrl+C overlap.
            pass
        except Exception:
            pass

        try:
            self._server.server_close()
        except Exception:
            pass

        try:
            if thread.is_alive():
                thread.join(timeout=1.0)
        except KeyboardInterrupt:
            pass

    def reconfigure(self, port: int) -> None:
        if port == self.port:
            return
        was_running = self._thread is not None and self._thread.is_alive()
        if was_running:
            self.stop()
        self.port = port
        self._server = self._create_server()
        if was_running:
            self.start()

    def _build_handler(self):
        selection_service = self.selection_service
        state_endpoint = self.state_endpoint

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path == "/obs-player":
                    clip = selection_service.get_selected_clip()
                    state = selection_service.get_state()
                    body = build_player_page(
                        clip,
                        state.updated_at.isoformat() if state.updated_at else None,
                    ).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                if parsed.path == "/api/player-state":
                    payload = json.dumps(state_endpoint.build_payload()).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                self.send_response(404)
                self.end_headers()

            def do_POST(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path == "/api/clear-selection":
                    selection_service.clear_selection()
                    payload = json.dumps({"ok": True}).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                self.send_response(404)
                self.end_headers()

            def log_message(self, format: str, *args) -> None:
                return

        return Handler

    def _create_server(self) -> HTTPServer:
        return HTTPServer((self.host, self.port), self._build_handler())
