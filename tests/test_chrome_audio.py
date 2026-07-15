from __future__ import annotations

import io
import subprocess
import tempfile
import unittest
from pathlib import Path

from bizneo_recorder.chrome_audio import (
    ChromeAudioClient,
    ChromeAudioError,
)


class FakeProcess:
    def __init__(
        self,
        stdout: str = "READY\n",
        stderr: str = "",
        returncode: int = 0,
    ) -> None:
        self.stdin = io.StringIO()
        self.stdout = io.StringIO(stdout)
        self.stderr = io.StringIO(stderr)
        self.returncode = returncode
        self.killed = False

    def poll(self) -> int | None:
        return None if self.returncode == 0 else self.returncode

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode

    def kill(self) -> None:
        self.killed = True


class ProcessFactory:
    def __init__(self, process: FakeProcess) -> None:
        self.process = process
        self.command: list[str] | None = None

    def __call__(self, command: list[str], **_kwargs: object) -> FakeProcess:
        self.command = command
        return self.process


class ChromeAudioClientTests(unittest.TestCase):
    def test_start_waits_for_ready_line_and_builds_expected_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "chrome.wav"
            factory = ProcessFactory(FakeProcess())
            client = ChromeAudioClient(Path("helper.exe"), process_factory=factory)

            handle = client.start(321, output)

        self.assertEqual(handle.pid, 321)
        self.assertEqual(factory.command, ["helper.exe", "321", str(output)])

    def test_start_reports_helper_diagnostic_before_ready(self) -> None:
        process = FakeProcess(stdout="", stderr="activation failed", returncode=3)
        client = ChromeAudioClient(
            Path("helper.exe"),
            process_factory=ProcessFactory(process),
        )

        with self.assertRaisesRegex(ChromeAudioError, "activation failed"):
            client.start(321, Path("chrome.wav"))

    def test_stop_sends_q_and_accepts_valid_wav(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "chrome.wav"
            process = FakeProcess()
            handle = ChromeAudioClient(
                Path("helper.exe"),
                process_factory=ProcessFactory(process),
            ).start(321, output)
            output.write_bytes(b"RIFF" + b"\0" * 40)

            handle.stop()

        self.assertEqual(process.stdin.getvalue(), "q\n")

    def test_diagnose_runs_helper_self_test(self) -> None:
        completed = subprocess.CompletedProcess(
            ["helper.exe", "--self-test"],
            0,
            "Captura de audio por proceso: compatible\n",
            "",
        )
        calls: list[list[str]] = []

        def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return completed

        diagnostic = ChromeAudioClient(
            Path("helper.exe"),
            run_factory=runner,
        ).diagnose()

        self.assertTrue(diagnostic.supported)
        self.assertEqual(calls, [["helper.exe", "--self-test"]])


if __name__ == "__main__":
    unittest.main()
