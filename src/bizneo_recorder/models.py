from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Microphone:
    """A DirectShow microphone exposed by FFmpeg."""

    name: str
    alternative_name: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("microphone name cannot be empty")


@dataclass(frozen=True, slots=True)
class ResolutionPreset:
    """A user-facing output size supported by the recorder UI."""

    label: str
    width: int
    height: int


RESOLUTION_PRESETS: tuple[ResolutionPreset, ...] = (
    ResolutionPreset("HD 720p", 1280, 720),
    ResolutionPreset("Full HD 1080p", 1920, 1080),
)
SUPPORTED_FPS: tuple[int, ...] = (30, 60)


def get_resolution_preset(label: str) -> ResolutionPreset:
    for preset in RESOLUTION_PRESETS:
        if preset.label == label:
            return preset
    raise ValueError(f"resolució no admesa: {label!r}")


def parse_fps(label: str) -> int:
    labels = {f"{fps} FPS": fps for fps in SUPPORTED_FPS}
    try:
        return labels[label]
    except KeyError as error:
        raise ValueError(f"FPS no admesos: {label!r}") from error


@dataclass(frozen=True, slots=True)
class RecordingPaths:
    """All final and temporary paths owned by one recording session."""

    final: Path
    partial: Path
    capture: Path
    chrome_audio: Path

    def intermediates(self) -> tuple[Path, Path, Path]:
        return self.partial, self.capture, self.chrome_audio


@dataclass(frozen=True, slots=True)
class RecordingConfig:
    """Validated values required to start one recording."""

    output_dir: Path
    chrome_process_id: int
    microphone: Microphone | None = None
    width: int = 1920
    height: int = 1080
    fps: int = 30

    def __post_init__(self) -> None:
        if self.chrome_process_id <= 0:
            raise ValueError("el PID de Chrome ha de ser positiu")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("recording dimensions must be positive")
        if self.fps <= 0:
            raise ValueError("recording frame rate must be positive")
        object.__setattr__(self, "output_dir", Path(self.output_dir))

    def next_paths(self, now: datetime | None = None) -> RecordingPaths:
        stamp = (now or datetime.now()).strftime("%Y-%m-%d-%H%M%S")
        stem = f"Conference-{stamp}"
        counter = 2

        def build_paths(candidate_stem: str) -> RecordingPaths:
            return RecordingPaths(
                final=self.output_dir / f"{candidate_stem}.mp4",
                partial=self.output_dir / f"{candidate_stem}.part.mp4",
                capture=self.output_dir / f"{candidate_stem}.capture.mkv",
                chrome_audio=self.output_dir / f"{candidate_stem}.chrome.wav",
            )

        paths = build_paths(stem)
        while any(path.exists() for path in (paths.final, *paths.intermediates())):
            paths = build_paths(f"{stem}-{counter}")
            counter += 1

        return paths

