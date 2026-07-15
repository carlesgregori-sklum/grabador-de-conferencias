from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = (
    *sorted((PROJECT_ROOT / "src" / "bizneo_recorder").glob("*.py")),
    PROJECT_ROOT / "src" / "bizneo_recorder" / "assets" / "browser_capture.html",
    PROJECT_ROOT / "native" / "chrome_audio_capture" / "ChromeAudioCapture.cs",
)
FORBIDDEN_USER_TEXT = (
    "No s'ha",
    "S'ha ",
    "No hi ha",
    "Encara no",
    "Ja hi ha",
    "gravació",
    "Gravació",
    "gravació",
    "pestanya",
    "micròfon",
    "àudio",
    "fitxer",
    "finestra",
    "seqüència",
    "pont local",
    "no és vàlid",
    "ha finalitzat",
    "ha creat",
    "ha pogut",
    "ha tancat",
    "ha començat",
    "microphone name cannot be empty",
    "unknown orbital state",
    "Usage:",
    "PID must be a positive integer",
    "Process loopback requires",
    "Chrome audio capture failed",
    "Completion handler:",
    "Format: PCM",
)


class RuntimeLocalizationTests(unittest.TestCase):
    def test_user_facing_runtime_text_is_spanish(self) -> None:
        occurrences: list[str] = []
        for path in RUNTIME_FILES:
            source = path.read_text(encoding="utf-8")
            for forbidden in FORBIDDEN_USER_TEXT:
                if forbidden in source:
                    occurrences.append(f"{path.relative_to(PROJECT_ROOT)}: {forbidden}")

        self.assertEqual(occurrences, [])


if __name__ == "__main__":
    unittest.main()
