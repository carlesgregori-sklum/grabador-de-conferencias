from __future__ import annotations

import subprocess
import threading
from collections import deque
from collections.abc import Callable
from enum import Enum, auto
from pathlib import Path
from typing import Any

from .browser_capture import BrowserCaptureBridge, BrowserCaptureError
from .chrome_audio import ChromeAudioClient, ChromeAudioError, ChromeAudioProcess
from .ffmpeg import FFmpegClient, FFmpegError
from .models import CaptureMode, RecordingConfig, RecordingPaths


class RecorderError(RuntimeError):
    """Raised when a recording cannot start or be finalized safely."""


class RecorderState(Enum):
    IDLE = auto()
    RECORDING = auto()
    STOPPING = auto()


ProcessFactory = Callable[..., Any]
BrowserCaptureFactory = Callable[
    [RecordingConfig, RecordingPaths],
    BrowserCaptureBridge,
]


class Recorder:
    """Coordinates the selected video source, Chrome audio and final MP4."""

    def __init__(
        self,
        client: FFmpegClient,
        chrome_audio: ChromeAudioClient,
        process_factory: ProcessFactory = subprocess.Popen,
        *,
        browser_capture_factory: BrowserCaptureFactory | None = None,
    ) -> None:
        self.client = client
        self.chrome_audio = chrome_audio
        self._process_factory = process_factory
        self._browser_capture_factory = browser_capture_factory
        self._ffmpeg_process: Any | None = None
        self._chrome_process: ChromeAudioProcess | Any | None = None
        self._browser_capture: BrowserCaptureBridge | Any | None = None
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

    def start(
        self,
        config: RecordingConfig,
        chrome_executable: Path | None = None,
    ) -> Path:
        if self.state is not RecorderState.IDLE:
            raise RecorderError("Ja hi ha una gravació en marxa.")

        config.output_dir.mkdir(parents=True, exist_ok=True)
        self._paths = config.next_paths()
        self._config = config
        self._stderr_lines.clear()
        self.last_error = ""

        try:
            if config.capture_mode is CaptureMode.PRIMARY_SCREEN:
                self._start_primary_screen(config)
            else:
                self._start_browser_capture(config, chrome_executable)
        except (BrowserCaptureError, ChromeAudioError, FFmpegError, RecorderError, OSError, RuntimeError, ValueError) as error:
            self._abort_live_components()
            self._remove_intermediates()
            self._reset_live_state()
            if isinstance(error, RecorderError):
                raise
            raise RecorderError(str(error)) from error

        self.state = RecorderState.RECORDING
        return self.paths.final

    def _start_primary_screen(self, config: RecordingConfig) -> None:
        self._start_chrome_audio(config)
        command = self.client.build_capture_command(config, self.paths.capture)
        try:
            self._start_ffmpeg(command)
        except RecorderError as error:
            raise RecorderError(
                f"No s'ha pogut iniciar la captura de pantalla: {error}"
            ) from error

    def _start_browser_capture(
        self,
        config: RecordingConfig,
        chrome_executable: Path | None,
    ) -> None:
        if chrome_executable is None:
            raise RecorderError("No s'ha trobat l'executable de Chrome.")
        if self._browser_capture_factory is None:
            raise RecorderError("El selector de Chrome no està disponible.")

        bridge = self._browser_capture_factory(config, self.paths)
        self._browser_capture = bridge
        bridge.start(chrome_executable)
        bridge.wait_ready()

        if config.capture_mode is CaptureMode.SELECTED_MONITOR:
            self._start_chrome_audio(config)
        if config.microphone is not None:
            command = self.client.build_microphone_command(
                config,
                self.paths.microphone_audio,
            )
            try:
                self._start_ffmpeg(command)
            except RecorderError as error:
                raise RecorderError(
                    f"No s'ha pogut iniciar el micròfon: {error}"
                ) from error
        bridge.begin()

    def _start_chrome_audio(self, config: RecordingConfig) -> None:
        try:
            self._chrome_process = self.chrome_audio.start(
                config.chrome_process_id,
                self.paths.chrome_audio,
            )
        except (ChromeAudioError, OSError) as error:
            raise RecorderError(
                f"No s'ha pogut iniciar l'àudio de Chrome: {error}"
            ) from error

    def _start_ffmpeg(self, command: list[str]) -> None:
        try:
            process = self._process_factory(
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
            raise RecorderError(str(error)) from error
        self._ffmpeg_process = process
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr,
            args=(process,),
            name="ffmpeg-stderr",
            daemon=True,
        )
        self._stderr_thread.start()

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
        if self._browser_capture is not None:
            browser_error = self._browser_capture.poll()
            if browser_error:
                self.last_error = browser_error
                return 1
        if self._ffmpeg_process is not None:
            ffmpeg_code = self._ffmpeg_process.poll()
            if ffmpeg_code is not None:
                return ffmpeg_code
        if self._chrome_process is not None:
            chrome_code = self._chrome_process.poll()
            if chrome_code is not None:
                return chrome_code
        return None

    def stop(self, timeout: float = 15.0) -> Path:
        if self.state is not RecorderState.RECORDING or self._config is None:
            raise RecorderError("No hi ha cap gravació en marxa.")

        self.state = RecorderState.STOPPING
        try:
            self._stop_sources(timeout)
            self._validate_capture_file(self._config)
            self.client.run_finalize(self._config, self.paths)
            if not self.paths.partial.is_file():
                raise RecorderError("FFmpeg no ha creat l'MP4 final temporal.")
            self.paths.partial.replace(self.paths.final)
            self._remove_intermediates()
            return self.paths.final
        except (BrowserCaptureError, ChromeAudioError, FFmpegError, RecorderError, OSError, RuntimeError) as error:
            self.last_error = str(error)
            raise RecorderError(str(error)) from error
        finally:
            self._close_browser_capture()
            if self._stderr_thread is not None:
                self._stderr_thread.join(timeout=1.0)
            self._reset_live_state()

    def _stop_sources(self, timeout: float) -> None:
        errors: list[str] = []
        config = self._config
        if config is None:
            raise RecorderError("No hi ha cap configuració activa.")

        if self._browser_capture is not None:
            try:
                self._browser_capture.stop(timeout=timeout)
            except (BrowserCaptureError, OSError, RuntimeError) as error:
                errors.append(str(error))

        if self._ffmpeg_process is not None:
            try:
                self._stop_ffmpeg(timeout)
            except RecorderError as error:
                errors.append(str(error))

        if self._chrome_process is not None:
            try:
                self._chrome_process.stop(timeout=min(timeout, 10.0))
            except (ChromeAudioError, OSError, RuntimeError) as error:
                errors.append(str(error))

        if errors:
            raise RecorderError(errors[0])

    def _validate_capture_file(self, config: RecordingConfig) -> None:
        if config.capture_mode is CaptureMode.PRIMARY_SCREEN:
            if not self.paths.capture.is_file():
                raise RecorderError(
                    "La captura de pantalla no ha creat el fitxer temporal."
                )
        elif not self.paths.browser_capture.is_file():
            raise RecorderError("Chrome no ha creat el vídeo temporal.")

    def _stop_ffmpeg(self, timeout: float) -> None:
        process = self._ffmpeg_process
        if process is None:
            return
        try:
            if process.stdin is not None:
                process.stdin.write("q\n")
                process.stdin.flush()
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            return_code = process.wait(timeout=5.0)
            self._stderr_lines.append("FFmpeg no s'ha aturat dins del temps esperat.")
        except (BrokenPipeError, OSError, ValueError) as error:
            return_code = process.poll()
            self._stderr_lines.append(str(error))
            if return_code is None:
                process.kill()
                return_code = process.wait(timeout=5.0)

        if return_code != 0:
            diagnostic = "\n".join(list(self._stderr_lines)[-8:]).strip()
            raise RecorderError(
                diagnostic or f"FFmpeg ha finalitzat amb el codi {return_code}."
            )

    def _abort_live_components(self) -> None:
        self._close_browser_capture()
        process = self._ffmpeg_process
        if process is not None:
            try:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5.0)
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                pass
        if self._chrome_process is not None:
            try:
                self._chrome_process.stop()
            except (ChromeAudioError, OSError, RuntimeError):
                pass

    def _close_browser_capture(self) -> None:
        if self._browser_capture is None:
            return
        try:
            self._browser_capture.close()
        except (BrowserCaptureError, OSError, RuntimeError):
            pass

    def _remove_intermediates(self) -> None:
        if self._paths is None:
            return
        for path in self._paths.intermediates():
            path.unlink(missing_ok=True)

    def _reset_live_state(self) -> None:
        self._ffmpeg_process = None
        self._chrome_process = None
        self._browser_capture = None
        self._config = None
        self._stderr_thread = None
        self.state = RecorderState.IDLE
