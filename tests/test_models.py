from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from bizneo_recorder.models import Microphone, RecordingConfig


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
