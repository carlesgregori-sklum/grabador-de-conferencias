from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from bizneo_recorder.browser_capture import (
    BrowserCaptureBridge,
    BrowserCaptureError,
    BrowserCaptureMetadata,
)
from bizneo_recorder.models import CaptureMode


PAGE = """<!doctype html><script>window.CAPTURE_CONFIG=__CAPTURE_CONFIG__;</script>"""


class FakeProcessFactory:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def __call__(self, command: list[str], **kwargs: object) -> object:
        self.calls.append((command, kwargs))
        return object()


class BrowserCaptureBridgeTests(unittest.TestCase):
    def test_packaged_page_uses_display_media_and_ordered_chunks(self) -> None:
        page = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "bizneo_recorder"
            / "assets"
            / "browser_capture.html"
        ).read_text(encoding="utf-8")

        self.assertIn("getDisplayMedia", page)
        self.assertIn("MediaRecorder", page)
        self.assertIn("__CAPTURE_CONFIG__", page)
        self.assertIn("uploadChain", page)
        self.assertIn("class RetryableSelectionError", page)
        self.assertIn("error instanceof RetryableSelectionError", page)

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "capture.webm"
        self.factory = FakeProcessFactory()
        self.bridges: list[BrowserCaptureBridge] = []

    def make_bridge(
        self,
        mode: CaptureMode = CaptureMode.SELECTED_MONITOR,
    ) -> BrowserCaptureBridge:
        bridge = BrowserCaptureBridge(
            PAGE,
            mode,
            self.output,
            30,
            process_factory=self.factory,
            token_factory=lambda _bytes: "test-token",
        )
        bridge.start(Path(r"C:\Chrome\chrome.exe"))
        self.bridges.append(bridge)
        self.addCleanup(bridge.close)
        return bridge

    def request(
        self,
        bridge: BrowserCaptureBridge,
        method: str,
        path: str,
        data: bytes | None = None,
        content_type: str = "application/octet-stream",
    ) -> tuple[int, bytes]:
        request = Request(
            f"{bridge.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": content_type},
        )
        with urlopen(request, timeout=3) as response:
            return response.status, response.read()

    def post_json(
        self,
        bridge: BrowserCaptureBridge,
        path: str,
        payload: dict[str, object],
    ) -> tuple[int, bytes]:
        return self.request(
            bridge,
            "POST",
            path,
            json.dumps(payload).encode("utf-8"),
            "application/json",
        )

    def wait_for_command(
        self,
        bridge: BrowserCaptureBridge,
        expected: str,
    ) -> None:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            _, body = self.request(
                bridge,
                "GET",
                "/api/test-token/command",
            )
            if json.loads(body)["command"] == expected:
                return
            time.sleep(0.01)
        self.fail(f"Command {expected!r} was not exposed")

    def test_starts_on_loopback_and_launches_chrome_app_window(self) -> None:
        bridge = self.make_bridge()

        self.assertTrue(bridge.base_url.startswith("http://127.0.0.1:"))
        command, kwargs = self.factory.calls[0]
        self.assertEqual(command[0], r"C:\Chrome\chrome.exe")
        self.assertTrue(command[1].startswith("--app=http://127.0.0.1:"))
        self.assertIn("/capture/test-token", command[1])
        self.assertIn("creationflags", kwargs)

    def test_serves_page_with_session_configuration(self) -> None:
        bridge = self.make_bridge(CaptureMode.CHROME_TAB)

        _, body = self.request(
            bridge,
            "GET",
            "/capture/test-token",
        )

        html = body.decode("utf-8")
        self.assertIn('"mode": "tab"', html)
        self.assertIn('"fps": 30', html)
        self.assertNotIn("__CAPTURE_CONFIG__", html)

    def test_rejects_wrong_token(self) -> None:
        bridge = self.make_bridge()

        with self.assertRaises(HTTPError) as error:
            self.request(bridge, "GET", "/api/wrong/command")

        self.assertEqual(error.exception.code, 404)

    def test_ready_accepts_only_the_requested_surface(self) -> None:
        bridge = self.make_bridge()

        with self.assertRaises(HTTPError) as error:
            self.post_json(
                bridge,
                "/api/test-token/ready",
                {"display_surface": "browser", "has_audio": True, "mime_type": "x"},
            )
        self.assertEqual(error.exception.code, 422)

        self.post_json(
            bridge,
            "/api/test-token/ready",
            {"display_surface": "monitor", "has_audio": False, "mime_type": "x"},
        )
        self.assertEqual(
            bridge.wait_ready(timeout=1),
            BrowserCaptureMetadata("monitor", False, "x"),
        )

    def test_tab_requires_shared_audio(self) -> None:
        bridge = self.make_bridge(CaptureMode.CHROME_TAB)

        with self.assertRaises(HTTPError) as error:
            self.post_json(
                bridge,
                "/api/test-token/ready",
                {
                    "display_surface": "browser",
                    "has_audio": False,
                    "mime_type": "video/webm",
                },
            )

        self.assertEqual(error.exception.code, 422)

    def test_begin_waits_for_browser_started_signal(self) -> None:
        bridge = self.make_bridge()
        self.post_json(
            bridge,
            "/api/test-token/ready",
            {
                "display_surface": "monitor",
                "has_audio": False,
                "mime_type": "video/webm",
            },
        )
        completed: list[bool] = []
        thread = threading.Thread(
            target=lambda: (bridge.begin(timeout=2), completed.append(True))
        )
        thread.start()
        self.wait_for_command(bridge, "start")

        self.post_json(bridge, "/api/test-token/started", {})
        thread.join(timeout=2)

        self.assertEqual(completed, [True])

    def test_chunks_are_ordered_and_duplicate_retry_is_idempotent(self) -> None:
        bridge = self.make_bridge()

        self.request(bridge, "POST", "/api/test-token/chunk/0", b"webm-a")
        self.request(bridge, "POST", "/api/test-token/chunk/0", b"webm-a")
        self.request(bridge, "POST", "/api/test-token/chunk/1", b"webm-b")

        self.assertEqual(self.output.read_bytes(), b"webm-awebm-b")

    def test_rejects_chunk_sequence_gaps(self) -> None:
        bridge = self.make_bridge()

        with self.assertRaises(HTTPError) as error:
            self.request(bridge, "POST", "/api/test-token/chunk/1", b"bad")

        self.assertEqual(error.exception.code, 409)

    def test_rejects_oversized_chunk(self) -> None:
        bridge = self.make_bridge()
        bridge.MAX_CHUNK_BYTES = 4

        with self.assertRaises(HTTPError) as error:
            self.request(bridge, "POST", "/api/test-token/chunk/0", b"12345")

        self.assertEqual(error.exception.code, 413)

    def test_stop_waits_for_final_chunk_and_complete(self) -> None:
        bridge = self.make_bridge()
        self.request(bridge, "POST", "/api/test-token/chunk/0", b"webm")
        completed: list[bool] = []
        thread = threading.Thread(
            target=lambda: (bridge.stop(timeout=2), completed.append(True))
        )
        thread.start()
        self.wait_for_command(bridge, "stop")

        self.post_json(bridge, "/api/test-token/complete", {})
        thread.join(timeout=2)

        self.assertEqual(completed, [True])
        self.assertEqual(self.output.read_bytes(), b"webm")

    def test_browser_error_unblocks_waiters_and_poll(self) -> None:
        bridge = self.make_bridge()
        self.post_json(
            bridge,
            "/api/test-token/error",
            {"message": "Selecció cancel·lada."},
        )

        with self.assertRaisesRegex(BrowserCaptureError, "cancel·lada"):
            bridge.wait_ready(timeout=1)
        self.assertEqual(bridge.poll(), "Selecció cancel·lada.")


if __name__ == "__main__":
    unittest.main()
