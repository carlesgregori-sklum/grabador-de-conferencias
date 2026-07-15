from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bizneo_recorder.ffmpeg import FFmpegClient, FFmpegError, parse_dshow_audio_devices
from bizneo_recorder.models import CaptureMode, Microphone, RecordingConfig


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
    def test_capture_command_records_full_desktop_without_microphone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            config = RecordingConfig(output_dir, chrome_process_id=321)
            client = FFmpegClient(Path("ffmpeg.exe"))

            command = client.build_capture_command(
                config,
                output_dir / "recording.capture.mkv",
            )

        self.assertIn("desktop", command)
        self.assertNotIn("dshow", command)
        self.assertIn("libx264", command)
        self.assertIn("1920:1080", " ".join(command))
        self.assertEqual(command[-1], str(output_dir / "recording.capture.mkv"))

    def test_capture_command_adds_only_selected_microphone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            config = RecordingConfig(
                output_dir,
                chrome_process_id=321,
                microphone=Microphone("USB Microphone"),
            )
            command = FFmpegClient(Path("ffmpeg.exe")).build_capture_command(
                config,
                output_dir / "recording.capture.mkv",
            )

        self.assertIn("dshow", command)
        self.assertIn("audio=USB Microphone", command)
        self.assertIn("pcm_s16le", command)

    def test_capture_command_uses_selected_720p_60_profile(self) -> None:
        config = RecordingConfig(
            Path("videos"),
            chrome_process_id=321,
            width=1280,
            height=720,
            fps=60,
        )
        command = FFmpegClient(Path("ffmpeg.exe")).build_capture_command(
            config,
            Path("recording.capture.mkv"),
        )

        self.assertIn("1280:720", " ".join(command))
        self.assertGreaterEqual(command.count("60"), 2)

    def test_finalize_command_uses_chrome_as_only_audio_without_microphone(self) -> None:
        config = RecordingConfig(Path("videos"), chrome_process_id=321)
        paths = config.next_paths()

        command = FFmpegClient(Path("ffmpeg.exe")).build_finalize_command(
            config,
            paths,
        )

        self.assertIn(str(paths.chrome_audio), command)
        self.assertNotIn("amix", " ".join(command))
        self.assertIn("copy", command)
        self.assertIn("aac", command)
        self.assertEqual(command[-1], str(paths.partial))

    def test_finalize_command_mixes_chrome_and_microphone(self) -> None:
        config = RecordingConfig(
            Path("videos"),
            chrome_process_id=321,
            microphone=Microphone("USB Microphone"),
        )
        paths = config.next_paths()

        command = FFmpegClient(Path("ffmpeg.exe")).build_finalize_command(
            config,
            paths,
        )

        self.assertIn("amix=inputs=2", " ".join(command))
        self.assertIn("[a]", command)

    def test_microphone_command_records_only_the_selected_device(self) -> None:
        config = RecordingConfig(
            Path("videos"),
            chrome_process_id=321,
            microphone=Microphone("USB Microphone"),
            capture_mode=CaptureMode.CHROME_TAB,
        )
        paths = config.next_paths()

        command = FFmpegClient(Path("ffmpeg.exe")).build_microphone_command(
            config,
            paths.microphone_audio,
        )

        self.assertIn("audio=USB Microphone", command)
        self.assertIn("pcm_s16le", command)
        self.assertNotIn("gdigrab", command)
        self.assertEqual(command[-1], str(paths.microphone_audio))

    def test_selected_monitor_finalize_uses_browser_video_and_chrome_audio(self) -> None:
        config = RecordingConfig(
            Path("videos"),
            chrome_process_id=321,
            capture_mode=CaptureMode.SELECTED_MONITOR,
        )
        paths = config.next_paths()

        command = FFmpegClient(Path("ffmpeg.exe")).build_finalize_command(
            config,
            paths,
        )

        self.assertIn(str(paths.browser_capture), command)
        self.assertIn(str(paths.chrome_audio), command)
        self.assertNotIn(str(paths.capture), command)
        self.assertIn("libx264", command)
        self.assertNotIn("amix", " ".join(command))

    def test_selected_monitor_finalize_mixes_separate_microphone(self) -> None:
        config = RecordingConfig(
            Path("videos"),
            chrome_process_id=321,
            microphone=Microphone("USB Microphone"),
            capture_mode=CaptureMode.SELECTED_MONITOR,
        )
        paths = config.next_paths()

        command = FFmpegClient(Path("ffmpeg.exe")).build_finalize_command(
            config,
            paths,
        )

        self.assertIn(str(paths.microphone_audio), command)
        self.assertIn("amix=inputs=2", " ".join(command))

    def test_chrome_tab_finalize_uses_embedded_tab_audio(self) -> None:
        config = RecordingConfig(
            Path("videos"),
            chrome_process_id=321,
            capture_mode=CaptureMode.CHROME_TAB,
        )
        paths = config.next_paths()

        command = FFmpegClient(Path("ffmpeg.exe")).build_finalize_command(
            config,
            paths,
        )

        self.assertIn(str(paths.browser_capture), command)
        self.assertNotIn(str(paths.chrome_audio), command)
        self.assertNotIn(str(paths.capture), command)
        self.assertIn("0:a:0", command)
        self.assertIn("libx264", command)

    def test_chrome_tab_finalize_mixes_embedded_audio_and_microphone(self) -> None:
        config = RecordingConfig(
            Path("videos"),
            chrome_process_id=321,
            microphone=Microphone("USB Microphone"),
            capture_mode=CaptureMode.CHROME_TAB,
        )
        paths = config.next_paths()

        command = FFmpegClient(Path("ffmpeg.exe")).build_finalize_command(
            config,
            paths,
        )

        self.assertIn(str(paths.microphone_audio), command)
        self.assertNotIn(str(paths.chrome_audio), command)
        self.assertIn("amix=inputs=2", " ".join(command))

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

