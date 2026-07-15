from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import CaptureMode, Microphone, RecordingConfig, RecordingPaths


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

    def build_capture_command(
        self,
        config: RecordingConfig,
        capture_path: Path,
    ) -> list[str]:
        size = f"{config.width}:{config.height}"
        video_filter = (
            f"scale={size}:force_original_aspect_ratio=decrease,"
            f"pad={size}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        )
        command = [
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
        ]
        if config.microphone is None:
            command.extend(["-vf", video_filter, "-map", "0:v:0"])
        else:
            command.extend(
                [
                    "-thread_queue_size",
                    "1024",
                    "-f",
                    "dshow",
                    "-i",
                    f"audio={config.microphone.name}",
                    "-filter_complex",
                    f"[0:v]{video_filter}[v];"
                    "[1:a]aresample=44100:async=1:first_pts=0,"
                    "aformat=sample_fmts=s16:channel_layouts=stereo[mic]",
                    "-map",
                    "[v]",
                    "-map",
                    "[mic]",
                ]
            )
        command.extend(
            [
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
            ]
        )
        if config.microphone is not None:
            command.extend(["-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2"])
        command.append(str(capture_path))
        return command

    def build_microphone_command(
        self,
        config: RecordingConfig,
        microphone_path: Path,
    ) -> list[str]:
        if config.microphone is None:
            raise FFmpegError("No hi ha cap micròfon seleccionat.")
        return [
            str(self.executable),
            "-hide_banner",
            "-loglevel",
            "warning",
            "-y",
            "-thread_queue_size",
            "1024",
            "-f",
            "dshow",
            "-i",
            f"audio={config.microphone.name}",
            "-af",
            "aresample=44100:async=1:first_pts=0,"
            "aformat=sample_fmts=s16:channel_layouts=stereo",
            "-vn",
            "-c:a",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(microphone_path),
        ]

    def build_finalize_command(
        self,
        config: RecordingConfig,
        paths: RecordingPaths,
    ) -> list[str]:
        if config.capture_mode is not CaptureMode.PRIMARY_SCREEN:
            return self._build_browser_finalize_command(config, paths)

        command = [
            str(self.executable),
            "-hide_banner",
            "-loglevel",
            "warning",
            "-y",
            "-i",
            str(paths.capture),
            "-i",
            str(paths.chrome_audio),
        ]
        if config.microphone is None:
            command.extend(["-map", "0:v:0", "-map", "1:a:0"])
        else:
            command.extend(
                [
                    "-filter_complex",
                    "[1:a]aresample=44100:async=1:first_pts=0[chrome];"
                    "[0:a]aresample=44100:async=1:first_pts=0[mic];"
                    "[chrome][mic]amix=inputs=2:duration=longest:"
                    "dropout_transition=0,aresample=44100:async=1:first_pts=0[a]",
                    "-map",
                    "0:v:0",
                    "-map",
                    "[a]",
                ]
            )
        command.extend(
            [
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "44100",
                "-movflags",
                "+faststart",
                "-shortest",
                str(paths.partial),
            ]
        )
        return command

    def _build_browser_finalize_command(
        self,
        config: RecordingConfig,
        paths: RecordingPaths,
    ) -> list[str]:
        size = f"{config.width}:{config.height}"
        video_filter = (
            f"scale={size}:force_original_aspect_ratio=decrease,"
            f"pad={size}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        )
        command = [
            str(self.executable),
            "-hide_banner",
            "-loglevel",
            "warning",
            "-y",
            "-i",
            str(paths.browser_capture),
        ]

        if config.capture_mode is CaptureMode.SELECTED_MONITOR:
            command.extend(["-i", str(paths.chrome_audio)])
            source_audio_index = 1
        else:
            source_audio_index = 0

        if config.microphone is None:
            command.extend(
                [
                    "-vf",
                    video_filter,
                    "-map",
                    "0:v:0",
                    "-map",
                    f"{source_audio_index}:a:0",
                ]
            )
        else:
            microphone_index = source_audio_index + 1
            command.extend(["-i", str(paths.microphone_audio)])
            command.extend(
                [
                    "-filter_complex",
                    f"[0:v]{video_filter}[v];"
                    f"[{source_audio_index}:a]"
                    "aresample=44100:async=1:first_pts=0[source];"
                    f"[{microphone_index}:a]"
                    "aresample=44100:async=1:first_pts=0[mic];"
                    "[source][mic]amix=inputs=2:duration=longest:"
                    "dropout_transition=0,"
                    "aresample=44100:async=1:first_pts=0[a]",
                    "-map",
                    "[v]",
                    "-map",
                    "[a]",
                ]
            )

        command.extend(
            [
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
                "44100",
                "-movflags",
                "+faststart",
                "-shortest",
                str(paths.partial),
            ]
        )
        return command

    def run_finalize(self, config: RecordingConfig, paths: RecordingPaths) -> None:
        try:
            result = subprocess.run(
                self.build_finalize_command(config, paths),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
        except (FileNotFoundError, OSError) as error:
            raise FFmpegError(
                "No s'ha pogut obrir FFmpeg per finalitzar el vídeo."
            ) from error
        if result.returncode != 0:
            diagnostic = "\n".join(result.stderr.strip().splitlines()[-8:])
            raise FFmpegError(
                diagnostic
                or f"FFmpeg ha fallat en finalitzar amb el codi {result.returncode}."
            )

