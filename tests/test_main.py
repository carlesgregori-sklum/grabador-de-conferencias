from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bizneo_recorder.app import build_recording_config, format_elapsed
from bizneo_recorder.chrome_audio import ChromeAudioDiagnostic
from bizneo_recorder.ffmpeg import DiagnosticResult
from bizneo_recorder.main import resource_path, run_self_test
from bizneo_recorder.models import Microphone


class FakeDiagnosticClient:
    def __init__(self, result: DiagnosticResult) -> None:
        self.result = result

    def diagnose(self) -> DiagnosticResult:
        return self.result


class FakeChromeAudioClient:
    def __init__(self, supported: bool = True) -> None:
        self.supported = supported

    def diagnose(self) -> ChromeAudioDiagnostic:
        return ChromeAudioDiagnostic(
            self.supported,
            "Process loopback: supported" if self.supported else "unsupported",
        )


class MainTests(unittest.TestCase):
    def test_build_recording_config_supports_every_quality_combination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for resolution, expected_size in (
                ("HD 720p", (1280, 720)),
                ("Full HD 1080p", (1920, 1080)),
            ):
                for fps_label, expected_fps in (("30 FPS", 30), ("60 FPS", 60)):
                    with self.subTest(resolution=resolution, fps=fps_label):
                        config = build_recording_config(
                            Path(directory),
                            321,
                            False,
                            Microphone("Mic"),
                            resolution,
                            fps_label,
                        )
                        self.assertEqual((config.width, config.height), expected_size)
                        self.assertEqual(config.fps, expected_fps)
                        self.assertIsNone(config.microphone)

    def test_build_recording_config_includes_microphone_only_when_enabled(self) -> None:
        config = build_recording_config(
            Path("videos"),
            321,
            True,
            Microphone("Mic"),
            "Full HD 1080p",
            "30 FPS",
        )

        self.assertEqual(config.microphone, Microphone("Mic"))

    def test_resource_path_uses_executable_directory_when_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "Conference Recorder.exe"
            with (
                patch.object(sys, "frozen", True, create=True),
                patch.object(sys, "executable", str(executable)),
            ):
                path = resource_path("tools/ffmpeg.exe")

            self.assertEqual(path, Path(directory) / "tools" / "ffmpeg.exe")

    def test_format_elapsed_produces_minutes_and_seconds(self) -> None:
        self.assertEqual(format_elapsed(0), "00:00")
        self.assertEqual(format_elapsed(125.9), "02:05")

    def test_self_test_succeeds_without_microphone_or_running_chrome(self) -> None:
        output = io.StringIO()

        exit_code = run_self_test(
            FakeDiagnosticClient(DiagnosticResult(True, ())),
            FakeChromeAudioClient(),
            chrome_finder=lambda: None,
            output=output,
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("cap micròfon", output.getvalue())
        self.assertIn("Chrome: no està obert", output.getvalue())

    def test_self_test_reports_encoder_chrome_and_microphones(self) -> None:
        output = io.StringIO()
        client = FakeDiagnosticClient(
            DiagnosticResult(True, (Microphone("Micròfon integrat"),))
        )

        exit_code = run_self_test(
            client,
            FakeChromeAudioClient(),
            chrome_finder=lambda: 321,
            output=output,
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("H.264: correcte", output.getvalue())
        self.assertIn("Micròfon integrat", output.getvalue())
        self.assertIn("Chrome: detectat", output.getvalue())

    def test_self_test_fails_when_process_loopback_is_unavailable(self) -> None:
        output = io.StringIO()

        exit_code = run_self_test(
            FakeDiagnosticClient(DiagnosticResult(True, ())),
            FakeChromeAudioClient(False),
            chrome_finder=lambda: 321,
            output=output,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("Àudio de Chrome: error", output.getvalue())


if __name__ == "__main__":
    unittest.main()
