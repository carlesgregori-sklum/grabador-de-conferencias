from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELPER = PROJECT_ROOT / "work" / "test-helper" / "chrome-audio-capture.exe"


class ChromeAudioHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(PROJECT_ROOT / "scripts" / "build-chrome-audio.ps1"),
                "-OutputPath",
                str(HELPER),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(f"helper build failed:\n{result.stdout}\n{result.stderr}")

    def test_helper_self_test_reports_process_loopback_support(self) -> None:
        result = subprocess.run(
            [str(HELPER), "--self-test"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Captura de audio por proceso: compatible", result.stdout)
        self.assertIn("Controlador de finalización: ágil", result.stdout)

    def test_helper_rejects_invalid_pid(self) -> None:
        result = subprocess.run(
            [str(HELPER), "0", "capture.wav"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("PID", result.stderr)

    def test_helper_rejects_missing_arguments(self) -> None:
        result = subprocess.run(
            [str(HELPER)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Uso", result.stderr)


if __name__ == "__main__":
    unittest.main()
