from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from bizneo_recorder.models import Microphone, RecordingConfig
from bizneo_recorder.recorder import Recorder, RecorderError, RecorderState


class FakeClient:
    def build_record_command(
        self,
        config: RecordingConfig,
        working_path: Path,
    ) -> list[str]:
        return ["ffmpeg.exe", "-i", "desktop", str(working_path)]


class FakeStdin(io.StringIO):
    def close(self) -> None:
        self.was_closed = True


class FakeProcess:
    def __init__(self, returncode: int = 0) -> None:
        self.stdin = FakeStdin()
        self.stderr = io.StringIO("capture diagnostic\n")
        self.returncode = returncode
        self.killed = False

    def poll(self) -> int | None:
        return None

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode

    def kill(self) -> None:
        self.killed = True


class ProcessFactory:
    def __init__(self, process: FakeProcess) -> None:
        self.process = process
        self.command: list[str] | None = None
        self.kwargs: dict[str, object] | None = None

    def __call__(self, command: list[str], **kwargs: object) -> FakeProcess:
        self.command = command
        self.kwargs = kwargs
        return self.process


class RecorderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name) / "videos"
        self.config = RecordingConfig(Microphone("Mic"), self.output_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def make_recorder(self, returncode: int = 0) -> tuple[Recorder, FakeProcess]:
        process = FakeProcess(returncode)
        recorder = Recorder(FakeClient(), ProcessFactory(process))
        return recorder, process

    def test_start_transitions_to_recording_and_returns_final_path(self) -> None:
        recorder, _ = self.make_recorder()

        final_path = recorder.start(self.config)

        self.assertEqual(recorder.state, RecorderState.RECORDING)
        self.assertEqual(final_path.parent, self.output_dir)
        self.assertTrue(self.output_dir.is_dir())
        self.assertEqual(recorder.working_path.suffixes[-2:], [".part", ".mp4"])

    def test_start_rejects_second_recording(self) -> None:
        recorder, _ = self.make_recorder()
        recorder.start(self.config)

        with self.assertRaisesRegex(RecorderError, "marxa"):
            recorder.start(self.config)

    def test_successful_stop_sends_q_and_promotes_working_file(self) -> None:
        recorder, process = self.make_recorder()
        final_path = recorder.start(self.config)
        recorder.working_path.write_bytes(b"video")

        result = recorder.stop()

        self.assertEqual(result, final_path)
        self.assertEqual(final_path.read_bytes(), b"video")
        self.assertFalse(recorder.working_path.exists())
        self.assertEqual(process.stdin.getvalue(), "q\n")
        self.assertEqual(recorder.state, RecorderState.IDLE)

    def test_failed_stop_retains_working_file_and_diagnostic(self) -> None:
        recorder, _ = self.make_recorder(returncode=1)
        recorder.start(self.config)
        working_path = recorder.working_path
        working_path.write_bytes(b"recoverable")

        with self.assertRaisesRegex(RecorderError, "capture diagnostic"):
            recorder.stop()

        self.assertTrue(working_path.exists())
        self.assertEqual(recorder.state, RecorderState.IDLE)


if __name__ == "__main__":
    unittest.main()

