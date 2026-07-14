from __future__ import annotations

import subprocess
import threading
from collections import deque
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable

from .ffmpeg import FFmpegClient
from .models import RecordingConfig


class RecorderError(RuntimeError):
    """Raised when a recording cannot start or be finalized safely."""


class RecorderState(Enum):
    IDLE = auto()
    RECORDING = auto()
    STOPPING = auto()


ProcessFactory = Callable[..., Any]


class Recorder:
    """Owns one FFmpeg process and its safe file-finalization lifecycle."""

    def __init__(
        self,
        client: FFmpegClient,
        process_factory: ProcessFactory = subprocess.Popen,
    ) -> None:
        self.client = client
        self._process_factory = process_factory
        self._process: Any | None = None
        self._final_path: Path | None = None
        self._working_path: Path | None = None
        self._stderr_lines: deque[str] = deque(maxlen=80)
        self._stderr_thread: threading.Thread | None = None
        self.state = RecorderState.IDLE
        self.last_error = ""

    @property
    def final_path(self) -> Path:
        if self._final_path is None:
            raise RecorderError("Encara no hi ha cap gravació preparada.")
        return self._final_path

    @property
    def working_path(self) -> Path:
        if self._working_path is None:
            raise RecorderError("Encara no hi ha cap gravació preparada.")
        return self._working_path

    def start(self, config: RecordingConfig) -> Path:
        if self.state is not RecorderState.IDLE:
            raise RecorderError("Ja hi ha una gravació en marxa.")

        config.output_dir.mkdir(parents=True, exist_ok=True)
        final_path, working_path = config.next_paths()
        command = self.client.build_record_command(config, working_path)
        self._stderr_lines.clear()
        self.last_error = ""

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
            raise RecorderError(f"No s'ha pogut iniciar la gravació: {error}") from error

        self._process = process
        self._final_path = final_path
        self._working_path = working_path
        self.state = RecorderState.RECORDING
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr,
            args=(process,),
            name="ffmpeg-stderr",
            daemon=True,
        )
        self._stderr_thread.start()
        return final_path

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
        if self._process is None or self.state is RecorderState.IDLE:
            return None
        return self._process.poll()

    def stop(self, timeout: float = 15.0) -> Path:
        if self.state is not RecorderState.RECORDING or self._process is None:
            raise RecorderError("No hi ha cap gravació en marxa.")

        self.state = RecorderState.STOPPING
        process = self._process
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

        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=1.0)

        self.state = RecorderState.IDLE
        self._process = None

        if return_code == 0 and self.working_path.is_file():
            self.working_path.replace(self.final_path)
            return self.final_path

        diagnostics = "\n".join(list(self._stderr_lines)[-8:]).strip()
        if not diagnostics:
            diagnostics = f"FFmpeg ha finalitzat amb el codi {return_code}."
        self.last_error = diagnostics
        raise RecorderError(
            "La gravació no s'ha pogut finalitzar. "
            f"El fitxer temporal es conserva si existeix.\n\n{diagnostics}"
        )

