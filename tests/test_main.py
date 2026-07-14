from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bizneo_recorder.app import build_recording_config, format_elapsed
from bizneo_recorder.ffmpeg import DiagnosticResult
from bizneo_recorder.main import resource_path, run_self_test
from bizneo_recorder.models import Microphone


class FakeDiagnosticClient:
    def __init__(self, result: DiagnosticResult) -> None:
        self.result = result

    def diagnose(self) -> DiagnosticResult:
        return self.result


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
                            Microphone("Mic"),
                            Path(directory),
                            resolution,
                            fps_label,
                        )
                        self.assertEqual(
                            (config.width, config.height),
                            expected_size,
                        )
                        self.assertEqual(config.fps, expected_fps)

    def test_resource_path_uses_executable_directory_when_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "Bizneo Recorder.exe"
            with (
                patch.object(sys, "frozen", True, create=True),
                patch.object(sys, "executable", str(executable)),
            ):
                path = resource_path("tools/ffmpeg.exe")

            self.assertEqual(path, Path(directory) / "tools" / "ffmpeg.exe")

    def test_format_elapsed_produces_minutes_and_seconds(self) -> None:
        self.assertEqual(format_elapsed(0), "00:00")
        self.assertEqual(format_elapsed(125.9), "02:05")

    def test_self_test_fails_when_no_microphone_is_found(self) -> None:
        output = io.StringIO()
        client = FakeDiagnosticClient(DiagnosticResult(True, ()))

        exit_code = run_self_test(client, output)

        self.assertEqual(exit_code, 1)
        self.assertIn("cap micròfon", output.getvalue())

    def test_self_test_reports_encoder_and_microphones(self) -> None:
        output = io.StringIO()
        client = FakeDiagnosticClient(
            DiagnosticResult(True, (Microphone("Micròfon integrat"),))
        )

        exit_code = run_self_test(client, output)

        self.assertEqual(exit_code, 0)
        self.assertIn("H.264: correcte", output.getvalue())
        self.assertIn("Micròfon integrat", output.getvalue())


if __name__ == "__main__":
    unittest.main()
