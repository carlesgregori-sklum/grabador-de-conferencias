from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from bizneo_recorder.models import (
    CAPTURE_MODE_LABELS,
    RESOLUTION_PRESETS,
    SUPPORTED_FPS,
    CaptureMode,
    Microphone,
    RecordingConfig,
    get_resolution_preset,
    parse_capture_mode,
    parse_fps,
)


class RecordingQualityTests(unittest.TestCase):
    def test_capture_labels_map_to_three_modes(self) -> None:
        self.assertEqual(
            tuple(CAPTURE_MODE_LABELS),
            (
                "Pantalla completa",
                "Elegir pantalla",
                "Pestaña de Chrome",
            ),
        )
        self.assertEqual(
            parse_capture_mode("Pantalla completa"),
            CaptureMode.PRIMARY_SCREEN,
        )
        self.assertEqual(
            parse_capture_mode("Elegir pantalla"),
            CaptureMode.SELECTED_MONITOR,
        )
        self.assertEqual(
            parse_capture_mode("Pestaña de Chrome"),
            CaptureMode.CHROME_TAB,
        )

    def test_capture_mode_lookup_rejects_unknown_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "fuente de captura"):
            parse_capture_mode("Una ventana")

    def test_supported_resolution_presets_are_720p_and_1080p(self) -> None:
        self.assertEqual(
            [(item.label, item.width, item.height) for item in RESOLUTION_PRESETS],
            [
                ("HD 720p", 1280, 720),
                ("Full HD 1080p", 1920, 1080),
            ],
        )

    def test_supported_frame_rates_are_30_and_60(self) -> None:
        self.assertEqual(SUPPORTED_FPS, (30, 60))

    def test_resolution_lookup_rejects_unsupported_label(self) -> None:
        self.assertEqual(get_resolution_preset("HD 720p").width, 1280)
        with self.assertRaisesRegex(ValueError, "resolución"):
            get_resolution_preset("4K")

    def test_parse_fps_accepts_only_supported_labels(self) -> None:
        self.assertEqual(parse_fps("30 FPS"), 30)
        self.assertEqual(parse_fps("60 FPS"), 60)
        for unsupported in ("25 FPS", "60", "abc FPS"):
            with self.subTest(unsupported=unsupported):
                with self.assertRaisesRegex(ValueError, "FPS"):
                    parse_fps(unsupported)


class RecordingConfigTests(unittest.TestCase):
    def test_config_allows_chrome_audio_without_microphone(self) -> None:
        config = RecordingConfig(Path("videos"), chrome_process_id=321)

        self.assertIsNone(config.microphone)

    def test_next_paths_covers_every_intermediate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = RecordingConfig(Path(directory), chrome_process_id=321)

            paths = config.next_paths(datetime(2026, 7, 15, 9, 30, 0))

            self.assertEqual(paths.final.name, "Grabacion-2026-07-15-093000.mp4")
            self.assertEqual(
                paths.partial.name,
                "Grabacion-2026-07-15-093000.part.mp4",
            )
            self.assertEqual(
                paths.capture.name,
                "Grabacion-2026-07-15-093000.capture.mkv",
            )
            self.assertEqual(
                paths.chrome_audio.name,
                "Grabacion-2026-07-15-093000.chrome.wav",
            )
            self.assertEqual(
                paths.browser_capture.name,
                "Grabacion-2026-07-15-093000.browser.webm",
            )
            self.assertEqual(
                paths.microphone_audio.name,
                "Grabacion-2026-07-15-093000.microphone.wav",
            )

    def test_config_defaults_to_primary_screen(self) -> None:
        config = RecordingConfig(Path("videos"), chrome_process_id=321)

        self.assertIs(config.capture_mode, CaptureMode.PRIMARY_SCREEN)

    def test_next_paths_avoids_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            (output_dir / "Grabacion-2026-07-15-093000.chrome.wav").touch()
            config = RecordingConfig(output_dir, chrome_process_id=321)

            paths = config.next_paths(datetime(2026, 7, 15, 9, 30, 0))

            self.assertEqual(paths.final.name, "Grabacion-2026-07-15-093000-2.mp4")

    def test_config_rejects_empty_microphone_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "micrófono"):
                RecordingConfig(
                    Path(directory),
                    chrome_process_id=321,
                    microphone=Microphone("  "),
                )

    def test_config_rejects_invalid_chrome_pid(self) -> None:
        with self.assertRaisesRegex(ValueError, "Chrome"):
            RecordingConfig(Path("videos"), chrome_process_id=0)

    def test_config_rejects_invalid_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "dimensiones"):
                RecordingConfig(Path(directory), chrome_process_id=321, width=0)


if __name__ == "__main__":
    unittest.main()
