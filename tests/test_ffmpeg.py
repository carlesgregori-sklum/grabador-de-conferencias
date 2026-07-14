from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bizneo_recorder.ffmpeg import FFmpegClient, FFmpegError, parse_dshow_audio_devices
from bizneo_recorder.models import Microphone, RecordingConfig


DEVICE_OUTPUT = r'''
[dshow @ 000001] "Integrated Camera" (video)
[dshow @ 000001]   Alternative name "@device_pnp_camera"
[dshow @ 000001] "Microphone Array (Intel Smart Sound)" (audio)
[dshow @ 000001]   Alternative name "@device_cm_{AAA}\wave_{BBB}"
[dshow @ 000001] "Microphone Array (Intel Smart Sound)" (audio)
[dshow @ 000001] "USB Microphone" (audio)
'''


class DirectShowParserTests(unittest.TestCase):
    def test_parse_audio_devices_excludes_video_and_deduplicates(self) -> None:
        microphones = parse_dshow_audio_devices(DEVICE_OUTPUT)

        self.assertEqual(
            microphones,
            [
                Microphone(
                    "Microphone Array (Intel Smart Sound)",
                    r"@device_cm_{AAA}\wave_{BBB}",
                ),
                Microphone("USB Microphone"),
            ],
        )

    def test_parse_audio_devices_returns_empty_for_unrelated_output(self) -> None:
        self.assertEqual(parse_dshow_audio_devices("no DirectShow devices"), [])


class FFmpegClientTests(unittest.TestCase):
    def test_record_command_has_desktop_and_only_selected_microphone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            config = RecordingConfig(Microphone("Microphone Array"), output_dir)
            client = FFmpegClient(Path("ffmpeg.exe"))

            command = client.build_record_command(
                config,
                output_dir / "recording.part.mp4",
            )

        self.assertIn("desktop", command)
        self.assertIn("audio=Microphone Array", command)
        self.assertNotIn("Stereo Mix", command)
        self.assertIn("libx264", command)
        self.assertIn("aac", command)
        self.assertIn("1920:1080", " ".join(command))
        self.assertEqual(command[-1], str(output_dir / "recording.part.mp4"))

    @patch("bizneo_recorder.ffmpeg.subprocess.run")
    def test_list_microphones_parses_stderr_even_when_ffmpeg_returns_one(
        self,
        run: unittest.mock.Mock,
    ) -> None:
        run.return_value = subprocess.CompletedProcess([], 1, "", DEVICE_OUTPUT)
        client = FFmpegClient(Path("ffmpeg.exe"))

        microphones = client.list_microphones()

        self.assertEqual(len(microphones), 2)
        self.assertIn("-list_devices", run.call_args.args[0])

    def test_list_microphones_fails_when_ffmpeg_is_missing(self) -> None:
        client = FFmpegClient(Path("missing-ffmpeg.exe"))

        with self.assertRaisesRegex(FFmpegError, "FFmpeg"):
            client.list_microphones()


if __name__ == "__main__":
    unittest.main()

