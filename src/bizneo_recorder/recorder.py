from __future__ import annotations

import subprocess
import threading
from collections import deque
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable

from .chrome_audio import ChromeAudioClient, ChromeAudioError, ChromeAudioProcess
from .ffmpeg import FFmpegClient, FFmpegError
from .models import RecordingConfig, RecordingPaths


class RecorderError(RuntimeError):
    """Raised when a recording cannot start or be finalized safely."""


class RecorderState(Enum):
    IDLE = auto()
    RECORDING = auto()
    STOPPING = auto()


ProcessFactory = Callable[..., Any]


class Recorder:
    """Coordinates screen, Chrome audio and final MP4 ownership."""

    def __init__(
        self,
        client: FFmpegClient,
        chrome_audio: ChromeAudioClient,
        process_factory: ProcessFactory = subprocess.Popen,
    ) -> None:
        self.client = client
        self.chrome_audio = chrome_audio
        self._process_factory = process_factory
        self._screen_process: Any | None = None
        self._chrome_process: ChromeAudioProcess | Any | None = None
        self._paths: RecordingPaths | None = None
        self._config: RecordingConfig | None = None
        self._stderr_lines: deque[str] = deque(maxlen=80)
        self._stderr_thread: threading.Thread | None = None
        self.state = RecorderState.IDLE
        self.last_error = ""

    @property
    def paths(self) -> RecordingPaths:
        if self._paths is None:
            raise RecorderError("Encara no hi ha cap gravació preparada.")
        return self._paths

    @property
    def final_path(self) -> Path:
        return self.paths.final

    @property
    def working_path(self) -> Path:
        return self.paths.partial

    def start(self, config: RecordingConfig) -> Path:
        if self.state is not RecorderState.IDLE:
            raise RecorderError("Ja hi ha una gravació en marxa.")

        config.output_dir.mkdir(parents=True, exist_ok=True)
        self._paths = config.next_paths()
        self._config = config
        self._stderr_lines.clear()
        self.last_error = ""

        try:
            self._chrome_process = self.chrome_audio.start(
                config.chrome_process_id,
                self.paths.chrome_audio,
            )
        except (ChromeAudioError, OSError) as error:
            self._reset_live_state()
            raise RecorderError(
                f"No s'ha pogut iniciar l'àudio de Chrome: {error}"
            ) from error

        command = self.client.build_capture_command(config, self.paths.capture)
        try:
            screen_process = self._process_factory(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, ValueError) as error:
            self._stop_chrome_after_start_failure()
            self._reset_live_state()
            raise RecorderError(
                f"No s'ha pogut iniciar la captura de pantalla: {error}"
            ) from error

        self._screen_process = screen_process
        self.state = RecorderState.RECORDING
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr,
            args=(screen_process,),
            name="ffmpeg-stderr",
            daemon=True,
        )
        self._stderr_thread.start()
        return self.paths.final

    def _stop_chrome_after_start_failure(self) -> None:
        if self._chrome_process is None:
            return
        try:
            self._chrome_process.stop()
        except (ChromeAudioError, OSError):
            pass
        if self._paths is not None:
            self._paths.chrome_audio.unlink(missing_ok=True)

    def _drain_stderr(self, process: Any) -> None:
        stream = process.stderr
        if stream is None:
            return
        try:
            for line in stream:
                cleaned = line.strip()
                if cleaned:
                    self._stderr_lines.append(cleaned)
        except (OSError, ValueError):
            return

    def poll(self) -> int | None:
        if self.state is not RecorderState.RECORDING:
            return None
        if self._screen_process is not None:
            screen_code = self._screen_process.poll()
            if screen_code is not None:
                return screen_code
        if self._chrome_process is not None:
            chrome_code = self._chrome_process.poll()
            if chrome_code is not None:
                return chrome_code
        return None

    def stop(self, timeout: float = 15.0) -> Path:
        if (
            self.state is not RecorderState.RECORDING
            or self._screen_process is None
            or self._chrome_process is None
            or self._config is None
        ):
            raise RecorderError("No hi ha cap gravació en marxa.")

        self.state = RecorderState.STOPPING
        try:
            self._stop_screen(timeout)
            self._chrome_process.stop(timeout=min(timeout, 10.0))
            if not self.paths.capture.is_file():
                raise RecorderError(
                    "La captura de pantalla no ha creat el fitxer temporal."
                )
            self.client.run_finalize(self._config, self.paths)
            if not self.paths.partial.is_file():
                raise RecorderError("FFmpeg no ha creat l'MP4 final temporal.")
            self.paths.partial.replace(self.paths.final)
            self.paths.capture.unlink(missing_ok=True)
            self.paths.chrome_audio.unlink(missing_ok=True)
            return self.paths.final
        except (ChromeAudioError, FFmpegError, RecorderError, OSError, RuntimeError) as error:
            self.last_error = str(error)
            raise RecorderError(str(error)) from error
        finally:
            if self._stderr_thread is not None:
                self._stderr_thread.join(timeout=1.0)
            self._reset_live_state()

    def _stop_screen(self, timeout: float) -> None:
        process = self._screen_process
        if process is None:
            raise RecorderError("La captura de pantalla no està activa.")
        try:
            if process.stdin is not None:
                process.stdin.write("q\n")
                process.stdin.flush()
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            return_code = process.wait(timeout=5.0)
            self._stderr_lines.append(
                "FFmpeg no s'ha aturat dins del temps esperat."
            )
        except (BrokenPipeError, OSError, ValueError) as error:
            return_code = process.poll()
            self._stderr_lines.append(str(error))
            if return_code is None:
                process.kill()
                return_code = process.wait(timeout=5.0)

        if return_code != 0:
            diagnostic = "\n".join(list(self._stderr_lines)[-8:]).strip()
            raise RecorderError(
                diagnostic
                or f"La captura de pantalla ha finalitzat amb el codi {return_code}."
            )

    def _reset_live_state(self) -> None:
        self._screen_process = None
        self._chrome_process = None
        self._config = None
        self._stderr_thread = None
        self.state = RecorderState.IDLE
