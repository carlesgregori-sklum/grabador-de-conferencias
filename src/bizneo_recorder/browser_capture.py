from __future__ import annotations

import hashlib
import json
import secrets
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .models import CaptureMode


class BrowserCaptureError(RuntimeError):
    """Raised when Chrome cannot provide a complete selected-source capture."""


@dataclass(frozen=True, slots=True)
class BrowserCaptureMetadata:
    display_surface: str
    has_audio: bool
    mime_type: str


ProcessFactory = Callable[..., Any]
TokenFactory = Callable[[int], str]


class _BridgeServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        bridge: BrowserCaptureBridge,
    ) -> None:
        self.bridge = bridge
        super().__init__(address, _BridgeRequestHandler)


class _BridgeRequestHandler(BaseHTTPRequestHandler):
    server: _BridgeServer

    def log_message(self, _format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        bridge = self.server.bridge
        parts = self._path_parts()
        if parts == ["capture", bridge.token]:
            page = bridge.render_page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return
        if parts == ["api", bridge.token, "command"]:
            self._send_json(200, {"command": bridge.current_command})
            return
        self._send_json(404, {"error": "Ruta local no disponible."})

    def do_POST(self) -> None:  # noqa: N802
        bridge = self.server.bridge
        parts = self._path_parts()
        if len(parts) < 3 or parts[:2] != ["api", bridge.token]:
            self._send_json(404, {"error": "Ruta local no disponible."})
            return

        action = parts[2]
        if action == "ready" and len(parts) == 3:
            payload = self._read_json(4096)
            if payload is None:
                return
            try:
                bridge.accept_ready(payload)
            except BrowserCaptureError as error:
                self._send_json(422, {"error": str(error)})
                return
            self._send_json(204, None)
            return

        if action == "started" and len(parts) == 3:
            if not self._discard_small_body(4096):
                return
            bridge.accept_started()
            self._send_json(204, None)
            return

        if action == "chunk" and len(parts) == 4:
            try:
                sequence = int(parts[3])
            except ValueError:
                self._send_json(400, {"error": "Seqüència invàlida."})
                return
            body = self._read_body(bridge.MAX_CHUNK_BYTES)
            if body is None:
                return
            try:
                bridge.accept_chunk(sequence, body)
            except BrowserCaptureError as error:
                self._send_json(409, {"error": str(error)})
                return
            self._send_json(204, None)
            return

        if action == "complete" and len(parts) == 3:
            if not self._discard_small_body(4096):
                return
            bridge.accept_complete()
            self._send_json(204, None)
            return

        if action == "error" and len(parts) == 3:
            payload = self._read_json(4096)
            if payload is None:
                return
            message = payload.get("message")
            if not isinstance(message, str) or not message.strip():
                self._send_json(400, {"error": "Diagnòstic invàlid."})
                return
            bridge.accept_error(message.strip()[:1000])
            self._send_json(204, None)
            return

        self._send_json(404, {"error": "Ruta local no disponible."})

    def _path_parts(self) -> list[str]:
        return [part for part in self.path.partition("?")[0].split("/") if part]

    def _content_length(self) -> int | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Longitud invàlida."})
            return None
        if length < 0:
            self._send_json(400, {"error": "Longitud invàlida."})
            return None
        return length

    def _read_body(self, maximum: int) -> bytes | None:
        length = self._content_length()
        if length is None:
            return None
        if length > maximum:
            self._send_json(413, {"error": "Fragment massa gran."})
            return None
        return self.rfile.read(length)

    def _read_json(self, maximum: int) -> dict[str, object] | None:
        body = self._read_body(maximum)
        if body is None:
            return None
        try:
            value = json.loads(body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "JSON invàlid."})
            return None
        if not isinstance(value, dict):
            self._send_json(400, {"error": "JSON invàlid."})
            return None
        return value

    def _discard_small_body(self, maximum: int) -> bool:
        return self._read_body(maximum) is not None

    def _send_json(self, status: int, payload: object | None) -> None:
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Cache-Control", "no-store")
        if body:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)


class BrowserCaptureBridge:
    """Coordinates a single getDisplayMedia session over loopback HTTP."""

    MAX_CHUNK_BYTES = 16 * 1024 * 1024

    def __init__(
        self,
        page_html: str,
        mode: CaptureMode,
        output_path: Path,
        fps: int,
        process_factory: ProcessFactory = subprocess.Popen,
        token_factory: TokenFactory = secrets.token_urlsafe,
    ) -> None:
        if mode not in (CaptureMode.SELECTED_MONITOR, CaptureMode.CHROME_TAB):
            raise ValueError("el puente del navegador requiere monitor o pestaña")
        self.page_html = page_html
        self.mode = mode
        self.output_path = Path(output_path)
        self.fps = fps
        self._process_factory = process_factory
        self.token = token_factory(32)
        self._condition = threading.Condition()
        self._server: _BridgeServer | None = None
        self._server_thread: threading.Thread | None = None
        self._chrome_launcher: Any | None = None
        self._metadata: BrowserCaptureMetadata | None = None
        self._command = "wait"
        self._started = False
        self._completed = False
        self._error = ""
        self._expected_sequence = 0
        self._last_sequence = -1
        self._last_digest = b""

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise BrowserCaptureError("El puente local todavía no está abierto.")
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def current_command(self) -> str:
        with self._condition:
            return self._command

    def start(self, chrome_executable: Path) -> None:
        if self._server is not None:
            raise BrowserCaptureError("El puente local ya está abierto.")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._server = _BridgeServer(("127.0.0.1", 0), self)
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            kwargs={"poll_interval": 0.05},
            name="browser-capture-loopback",
            daemon=True,
        )
        self._server_thread.start()
        capture_url = f"{self.base_url}/capture/{self.token}"
        try:
            self._chrome_launcher = self._process_factory(
                [str(chrome_executable), f"--app={capture_url}"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, ValueError) as error:
            self.close()
            raise BrowserCaptureError(
                f"No se pudo abrir el selector en Chrome: {error}"
            ) from error

    def render_page(self) -> str:
        mode = "tab" if self.mode is CaptureMode.CHROME_TAB else "monitor"
        config = json.dumps(
            {"mode": mode, "fps": self.fps, "token": self.token},
            ensure_ascii=False,
        )
        return self.page_html.replace("__CAPTURE_CONFIG__", config)

    def accept_ready(self, payload: dict[str, object]) -> None:
        surface = payload.get("display_surface")
        has_audio = payload.get("has_audio")
        mime_type = payload.get("mime_type")
        if not isinstance(surface, str) or not isinstance(has_audio, bool):
            raise BrowserCaptureError("Chrome ha devuelto una fuente no válida.")
        if not isinstance(mime_type, str) or len(mime_type) > 128:
            raise BrowserCaptureError("Chrome ha devuelto un formato no válido.")
        if self.mode is CaptureMode.SELECTED_MONITOR and surface != "monitor":
            raise BrowserCaptureError("Selecciona una pantalla completa en Chrome.")
        if self.mode is CaptureMode.CHROME_TAB:
            if surface != "browser":
                raise BrowserCaptureError("Selecciona una pestaña de Chrome.")
            if not has_audio:
                raise BrowserCaptureError(
                    "Activa «Compartir también el audio» para grabar la pestaña."
                )
        metadata = BrowserCaptureMetadata(surface, has_audio, mime_type)
        with self._condition:
            if self._metadata is not None and self._metadata != metadata:
                raise BrowserCaptureError("La fuente seleccionada ya estaba preparada.")
            self._metadata = metadata
            self._condition.notify_all()

    def accept_started(self) -> None:
        with self._condition:
            self._started = True
            self._condition.notify_all()

    def accept_chunk(self, sequence: int, body: bytes) -> None:
        if sequence < 0:
            raise BrowserCaptureError("La secuencia del fragment no es válida.")
        digest = hashlib.sha256(body).digest()
        with self._condition:
            if sequence == self._last_sequence and digest == self._last_digest:
                return
            if sequence != self._expected_sequence:
                raise BrowserCaptureError(
                    f"Se esperaba el fragmento {self._expected_sequence}."
                )
            with self.output_path.open("ab") as stream:
                stream.write(body)
            self._last_sequence = sequence
            self._last_digest = digest
            self._expected_sequence += 1

    def accept_complete(self) -> None:
        with self._condition:
            self._completed = True
            self._condition.notify_all()

    def accept_error(self, message: str) -> None:
        with self._condition:
            if not self._error:
                self._error = message
            self._condition.notify_all()

    def wait_ready(self, timeout: float = 120.0) -> BrowserCaptureMetadata:
        with self._condition:
            ready = self._condition.wait_for(
                lambda: self._metadata is not None or bool(self._error),
                timeout=timeout,
            )
            self._raise_error_locked()
            if not ready or self._metadata is None:
                raise BrowserCaptureError(
                    "Se agotó el tiempo para seleccionar la fuente en Chrome."
                )
            return self._metadata

    def begin(self, timeout: float = 10.0) -> None:
        with self._condition:
            if self._metadata is None:
                raise BrowserCaptureError("Chrome todavía no ha preparado la fuente.")
            self._command = "start"
            self._condition.notify_all()
            started = self._condition.wait_for(
                lambda: self._started or bool(self._error),
                timeout=timeout,
            )
            self._raise_error_locked()
            if not started:
                raise BrowserCaptureError("Chrome no ha iniciado la grabación.")

    def stop(self, timeout: float = 15.0) -> None:
        with self._condition:
            self._command = "stop"
            self._condition.notify_all()
            completed = self._condition.wait_for(
                lambda: self._completed or bool(self._error),
                timeout=timeout,
            )
            self._raise_error_locked()
            if not completed:
                raise BrowserCaptureError("Chrome no cerró la grabación a tiempo.")
        if not self.output_path.is_file() or self.output_path.stat().st_size == 0:
            raise BrowserCaptureError("Chrome no ha creado el vídeo temporal.")

    def poll(self) -> str | None:
        with self._condition:
            return self._error or None

    def close(self) -> None:
        with self._condition:
            self._command = "abort"
            self._condition.notify_all()
        server = self._server
        thread = self._server_thread
        self._server = None
        self._server_thread = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=2.0)

    def _raise_error_locked(self) -> None:
        if self._error:
            raise BrowserCaptureError(self._error)
