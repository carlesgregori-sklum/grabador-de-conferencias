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

    def test_packages_and_validates_browser_capture_asset(self) -> None:
        script = (PROJECT_ROOT / "scripts" / "build-portable.ps1").read_text(
            encoding="utf-8"
        )
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("--add-data", script)
        self.assertIn("bizneo_recorder\\assets", script)
        self.assertIn("browser_capture.html", script)
        self.assertIn("[tool.setuptools.package-data]", pyproject)
        self.assertIn('bizneo_recorder = ["assets/*.html"]', pyproject)

    def test_portable_artifact_names_are_spanish(self) -> None:
        script = (PROJECT_ROOT / "scripts" / "build-portable.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn('"Grabador de conferencias.exe"', script)
        self.assertIn('"Grabador-de-conferencias-Portable.zip"', script)
        self.assertIn('"LEEME.txt"', script)
        self.assertNotIn("LLEGEIX-ME.txt", script)


if __name__ == "__main__":
    unittest.main()
