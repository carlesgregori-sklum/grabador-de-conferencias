from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import Microphone, RecordingConfig


class FFmpegError(RuntimeError):
    """Raised when FFmpeg is absent or cannot provide capture information."""


_AUDIO_DEVICE = re.compile(r'"(?P<name>.+)"\s+\(audio\)\s*$')
_ALTERNATIVE_NAME = re.compile(r'Alternative name\s+"(?P<name>.+)"\s*$')


def parse_dshow_audio_devices(text: str) -> list[Microphone]:
    """Extract DirectShow audio devices from FFmpeg diagnostic output."""

    microphones: list[Microphone] = []
    names_seen: set[str] = set()
    pending_index: int | None = None

    for line in text.splitlines():
        audio_match = _AUDIO_DEVICE.search(line)
        if audio_match:
            name = audio_match.group("name")
            if name in names_seen:
                pending_index = None
                continue
            names_seen.add(name)
            microphones.append(Microphone(name))
            pending_index = len(microphones) - 1
            continue

        alternative_match = _ALTERNATIVE_NAME.search(line)
        if alternative_match and pending_index is not None:
            current = microphones[pending_index]
            microphones[pending_index] = Microphone(
                current.name,
                alternative_match.group("name"),
            )
            pending_index = None

    return microphones


@dataclass(frozen=True, slots=True)
class DiagnosticResult:
    encoder_available: bool
    microphones: tuple[Microphone, ...]


class FFmpegClient:
    """Discovers capture devices and builds deterministic FFmpeg commands."""

    def __init__(self, executable: Path) -> None:
        self.executable = Path(executable)

    def _run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                [str(self.executable), *arguments],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
        except (FileNotFoundError, OSError) as error:
            raise FFmpegError(
                "No s'ha trobat FFmpeg. Torna a copiar la carpeta portàtil completa."
            ) from error

    def list_microphones(self) -> list[Microphone]:
        result = self._run(
            ["-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
        )
        microphones = parse_dshow_audio_devices(f"{result.stdout}\n{result.stderr}")
        return microphones

    def has_h264_encoder(self) -> bool:
        result = self._run(["-hide_banner", "-encoders"])
        return result.returncode == 0 and "libx264" in result.stdout

    def diagnose(self) -> DiagnosticResult:
        return DiagnosticResult(
            encoder_available=self.has_h264_encoder(),
            microphones=tuple(self.list_microphones()),
        )

    def build_record_command(
        self,
        config: RecordingConfig,
        working_path: Path,
    ) -> list[str]:
        size = f"{config.width}:{config.height}"
        video_filter = (
            f"[0:v]scale={size}:force_original_aspect_ratio=decrease,"
            f"pad={size}:(ow-iw)/2:(oh-ih)/2,setsar=1[v];"
            "[1:a]aresample=48000:async=1:first_pts=0[a]"
        )

        return [
            str(self.executable),
            "-hide_banner",
            "-loglevel",
            "warning",
            "-y",
            "-thread_queue_size",
            "1024",
            "-f",
            "gdigrab",
            "-framerate",
            str(config.fps),
            "-draw_mouse",
            "1",
            "-i",
            "desktop",
            "-thread_queue_size",
            "1024",
            "-f",
            "dshow",
            "-i",
            f"audio={config.microphone.name}",
            "-filter_complex",
            video_filter,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(config.fps),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(working_path),
        ]

