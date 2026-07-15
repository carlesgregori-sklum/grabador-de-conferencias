from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PortableBuildTests(unittest.TestCase):
    def test_uses_stable_onedir_bundle_without_runtime_extraction(self) -> None:
        script = (PROJECT_ROOT / "scripts" / "build-portable.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("--onedir", script)
        self.assertIn('--contents-directory "_runtime"', script)
        self.assertNotIn("--onefile", script)

    def test_waits_for_windowed_self_test_before_archiving(self) -> None:
        script = (PROJECT_ROOT / "scripts" / "build-portable.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("Start-Process", script)
        self.assertIn("-Wait", script)
        self.assertIn("$appSelfTest.ExitCode", script)


if __name__ == "__main__":
    unittest.main()
