from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from bizneo_recorder.models import (
    RESOLUTION_PRESETS,
    SUPPORTED_FPS,
    Microphone,
    RecordingConfig,
    get_resolution_preset,
    parse_fps,
)


class RecordingQualityTests(unittest.TestCase):
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
        with self.assertRaisesRegex(ValueError, "resolution"):
            get_resolution_preset("4K")

    def test_parse_fps_accepts_only_supported_labels(self) -> None:
        self.assertEqual(parse_fps("30 FPS"), 30)
        self.assertEqual(parse_fps("60 FPS"), 60)
        for unsupported in ("25 FPS", "60", "abc FPS"):
            with self.subTest(unsupported=unsupported):
                with self.assertRaisesRegex(ValueError, "frame rate"):
                    parse_fps(unsupported)


class RecordingConfigTests(unittest.TestCase):
    def test_next_paths_uses_timestamp_and_part_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = RecordingConfig(Microphone("Mic"), Path(directory))

            final, working = config.next_paths(datetime(2026, 7, 14, 15, 30, 10))

            self.assertEqual(final.name, "Bizneo-2026-07-14-153010.mp4")
            self.assertEqual(working.name, "Bizneo-2026-07-14-153010.part.mp4")

    def test_next_paths_avoids_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            (output_dir / "Bizneo-2026-07-14-153010.mp4").touch()
            config = RecordingConfig(Microphone("Mic"), output_dir)

            final, working = config.next_paths(datetime(2026, 7, 14, 15, 30, 10))

            self.assertEqual(final.name, "Bizneo-2026-07-14-153010-2.mp4")
            self.assertEqual(working.name, "Bizneo-2026-07-14-153010-2.part.mp4")

    def test_config_rejects_empty_microphone_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "microphone"):
                RecordingConfig(Microphone("  "), Path(directory))

    def test_config_rejects_invalid_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "dimensions"):
                RecordingConfig(Microphone("Mic"), Path(directory), width=0)


if __name__ == "__main__":
    unittest.main()
