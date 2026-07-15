from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from bizneo_recorder.chrome_audio import ChromeAudioError
from bizneo_recorder.models import RecordingConfig
from bizneo_recorder.recorder import Recorder, RecorderError, RecorderState


class FakeChromeHandle:
    def __init__(self, events: list[str], output_path: Path) -> None:
        self.events = events
        self.output_path = output_path
        self.stopped = False
        self.returncode: int | None = None

    def poll(self) -> int | None:
        return self.returncode

    def stop(self, timeout: float = 10.0) -> None:
        self.events.append("chrome-stopped")
        self.output_path.write_bytes(b"RIFF" + b"\0" * 40)
        self.stopped = True
        self.returncode = 0


class FakeChromeClient:
    def __init__(self, events: list[str], fail: bool = False) -> None:
        self.events = events
        self.fail = fail
        self.handle: FakeChromeHandle | None = None

    def start(self, process_id: int, output_path: Path) -> FakeChromeHandle:
        if self.fail:
            raise ChromeAudioError("chrome activation failed")
        self.events.append("chrome-ready")
        self.handle = FakeChromeHandle(self.events, output_path)
        return self.handle


class FakeFFmpegClient:
    def __init__(self, events: list[str], finalize_error: bool = False) -> None:
        self.events = events
        self.finalize_error = finalize_error

    def build_capture_command(self, config: RecordingConfig, capture_path: Path) -> list[str]:
        return ["ffmpeg.exe", "-i", "desktop", str(capture_path)]

    def run_finalize(self, config: RecordingConfig, paths: object) -> None:
        self.events.append("finalized")
        if self.finalize_error:
            raise RuntimeError("mux failed")
        paths.partial.write_bytes(b"mp4")


class FakeStdin(io.StringIO):
    def close(self) -> None:
        self.was_closed = True


class FakeScreenProcess:
    def __init__(self, events: list[str], returncode: int = 0) -> None:
        self.events = events
        self.stdin = FakeStdin()
        self.stderr = io.StringIO("screen diagnostic\n")
        self.returncode = returncode
        self.killed = False

    def poll(self) -> int | None:
        return None

    def wait(self, timeout: float | None = None) -> int:
        self.events.append("screen-stopped")
        return self.returncode

    def kill(self) -> None:
        self.killed = True


class ProcessFactory:
    def __init__(
        self,
        process: FakeScreenProcess,
        events: list[str],
        fail: bool = False,
    ) -> None:
        self.process = process
        self.events = events
        self.fail = fail
        self.command: list[str] | None = None

    def __call__(self, command: list[str], **_kwargs: object) -> FakeScreenProcess:
        if self.fail:
            raise OSError("screen process failed")
        self.command = command
        self.events.append("screen-started")
        return self.process


class RecorderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name) / "videos"
        self.config = RecordingConfig(self.output_dir, chrome_process_id=321)
        self.events: list[str] = []

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def make_recorder(
        self,
        *,
        screen_returncode: int = 0,
        screen_start_fails: bool = False,
        chrome_start_fails: bool = False,
        finalize_fails: bool = False,
    ) -> tuple[Recorder, FakeScreenProcess, FakeChromeClient]:
        screen = FakeScreenProcess(self.events, screen_returncode)
        chrome = FakeChromeClient(self.events, chrome_start_fails)
        recorder = Recorder(
            FakeFFmpegClient(self.events, finalize_fails),
            chrome,
            ProcessFactory(screen, self.events, screen_start_fails),
        )
        return recorder, screen, chrome

    def test_start_prepares_chrome_audio_before_screen_capture(self) -> None:
        recorder, _, _ = self.make_recorder()

        final_path = recorder.start(self.config)

        self.assertEqual(self.events[:2], ["chrome-ready", "screen-started"])
        self.assertEqual(recorder.state, RecorderState.RECORDING)
        self.assertEqual(final_path, recorder.paths.final)

    def test_start_rejects_second_recording(self) -> None:
        recorder, _, _ = self.make_recorder()
        recorder.start(self.config)

        with self.assertRaisesRegex(RecorderError, "marxa"):
            recorder.start(self.config)

    def test_screen_start_failure_stops_helper_and_resets_state(self) -> None:
        recorder, _, chrome = self.make_recorder(screen_start_fails=True)

        with self.assertRaisesRegex(RecorderError, "pantalla"):
            recorder.start(self.config)

        self.assertTrue(chrome.handle and chrome.handle.stopped)
        self.assertEqual(recorder.state, RecorderState.IDLE)

    def test_successful_stop_finalizes_and_removes_intermediates(self) -> None:
        recorder, screen, _ = self.make_recorder()
        final_path = recorder.start(self.config)
        recorder.paths.capture.write_bytes(b"capture")

        result = recorder.stop()

        self.assertEqual(result, final_path)
        self.assertEqual(final_path.read_bytes(), b"mp4")
        self.assertEqual(screen.stdin.getvalue(), "q\n")
        self.assertEqual(
            self.events[-3:],
            ["screen-stopped", "chrome-stopped", "finalized"],
        )
        self.assertFalse(recorder.paths.capture.exists())
        self.assertFalse(recorder.paths.chrome_audio.exists())
        self.assertEqual(recorder.state, RecorderState.IDLE)

    def test_finalize_failure_preserves_capture_and_chrome_wav(self) -> None:
        recorder, _, _ = self.make_recorder(finalize_fails=True)
        recorder.start(self.config)
        recorder.paths.capture.write_bytes(b"capture")

        with self.assertRaisesRegex(RecorderError, "mux failed"):
            recorder.stop()

        self.assertTrue(recorder.paths.capture.exists())
        self.assertTrue(recorder.paths.chrome_audio.exists())
        self.assertEqual(recorder.state, RecorderState.IDLE)


if __name__ == "__main__":
    unittest.main()
