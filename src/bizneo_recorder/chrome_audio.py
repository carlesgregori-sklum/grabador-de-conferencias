from __future__ import annotations

import queue
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TextIO


class ChromeAudioError(RuntimeError):
    """Raised when Chrome process-loopback capture cannot run safely."""


@dataclass(frozen=True, slots=True)
class ChromeAudioDiagnostic:
    supported: bool
    detail: str


ProcessFactory = Callable[..., Any]
RunFactory = Callable[..., subprocess.CompletedProcess[str]]


def _readline_with_timeout(stream: TextIO, timeout: float) -> str | None:
    result: queue.Queue[str] = queue.Queue(maxsize=1)

    def read() -> None:
        result.put(stream.readline())

    threading.Thread(target=read, name="chrome-audio-ready", daemon=True).start()
    try:
        return result.get(timeout=timeout)
    except queue.Empty:
        return None


def _bounded_stderr(process: Any) -> str:
    stream = getattr(process, "stderr", None)
    if stream is None:
        return ""
    try:
        text = stream.read()
    except (OSError, ValueError):
        return ""
    return "\n".join(text.strip().splitlines()[-8:])


@dataclass(slots=True)
class ChromeAudioProcess:
    pid: int
    output_path: Path
    process: Any

    def poll(self) -> int | None:
        return self.process.poll()

    def stop(self, timeout: float = 10.0) -> None:
        try:
            if self.process.stdin is not None:
                self.process.stdin.write("q\n")
                self.process.stdin.flush()
            return_code = self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            return_code = self.process.wait(timeout=5.0)
            raise ChromeAudioError(
                "La captura d'àudio de Chrome no s'ha aturat dins del temps esperat."
            )
        except (BrokenPipeError, OSError, ValueError) as error:
            raise ChromeAudioError(
                f"No s'ha pogut parar l'àudio de Chrome: {error}"
            ) from error

        if return_code != 0:
            diagnostic = _bounded_stderr(self.process)
            raise ChromeAudioError(
                diagnostic
                or f"El capturador d'àudio de Chrome ha finalitzat amb el codi {return_code}."
            )
        if not self.output_path.is_file() or self.output_path.stat().st_size < 44:
            raise ChromeAudioError(
                "El capturador de Chrome no ha creat un WAV vàlid."
            )


class ChromeAudioClient:
    """Starts and diagnoses the adjacent Windows process-loopback helper."""

    def __init__(
        self,
        executable: Path,
        process_factory: ProcessFactory = subprocess.Popen,
        run_factory: RunFactory = subprocess.run,
    ) -> None:
        self.executable = Path(executable)
        self._process_factory = process_factory
        self._run_factory = run_factory

    def diagnose(self) -> ChromeAudioDiagnostic:
        try:
            result = self._run_factory(
                [str(self.executable), "--self-test"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
        except (FileNotFoundError, OSError) as error:
            return ChromeAudioDiagnostic(False, str(error))
        detail = (result.stdout or result.stderr).strip()
        return ChromeAudioDiagnostic(result.returncode == 0, detail)

    def start(
        self,
        process_id: int,
        output_path: Path,
        ready_timeout: float = 10.0,
    ) -> ChromeAudioProcess:
        if process_id <= 0:
            raise ChromeAudioError("El PID de Chrome no és vàlid.")
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [str(self.executable), str(process_id), str(output_path)]
        try:
            process = self._process_factory(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (FileNotFoundError, OSError, ValueError) as error:
            raise ChromeAudioError(
                "No s'ha trobat el capturador d'àudio de Chrome. "
                "Conserva completa la carpeta portable."
            ) from error

        if process.stdout is None:
            process.kill()
            raise ChromeAudioError("El capturador de Chrome no té canal de control.")
        ready_line = _readline_with_timeout(process.stdout, ready_timeout)
        if ready_line is None:
            process.kill()
            process.wait(timeout=5.0)
            raise ChromeAudioError(
                "Windows no ha preparat l'àudio de Chrome dins del temps esperat."
            )
        if ready_line.strip() != "READY":
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5.0)
            diagnostic = _bounded_stderr(process)
            raise ChromeAudioError(
                diagnostic or "No s'ha pogut preparar l'àudio de Chrome."
            )
        return ChromeAudioProcess(process_id, output_path, process)
