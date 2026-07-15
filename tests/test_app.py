from __future__ import annotations

import tkinter as tk
import tempfile
import unittest
from pathlib import Path

from bizneo_recorder.app import BizneoRecorderApp
from bizneo_recorder.models import CAPTURE_MODE_LABELS, Microphone
from bizneo_recorder.processes import ChromeProcess
from bizneo_recorder.recorder import RecorderState


class FakeClient:
    def list_microphones(self) -> list[Microphone]:
        return [Microphone("USB Mic")]


class FakeRecorder:
    state = RecorderState.IDLE


class ConferenceRecorderUiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self) -> None:
        self.root.destroy()

    def test_initial_state_is_spanish_dark_and_ready(self) -> None:
        app = BizneoRecorderApp(
            self.root,
            FakeClient(),
            FakeRecorder(),
            chrome_finder=lambda: ChromeProcess(321, Path("chrome.exe")),
        )
        self.root.update_idletasks()

        self.assertEqual(self.root.title(), "Grabador de conferencias")
        self.assertFalse(app.include_microphone_var.get())
        self.assertEqual(app.microphone_panel.winfo_manager(), "")
        self.assertEqual(app.record_button.state, "normal")
        self.assertEqual(app.record_button.text, "Iniciar grabación")
        self.assertEqual(app.orbital_recorder.state, "ready")
        self.assertEqual(app.chrome_process_id, 321)
        self.assertEqual(app.capture_mode_var.get(), "Pantalla completa")
        self.assertEqual(len(app.capture_mode_cards), len(CAPTURE_MODE_LABELS))
        self.assertTrue(app.capture_mode_cards["Pantalla completa"].selected)
        self.assertEqual(app.hero_status_var.get(), "LISTO PARA GRABAR")

    def test_microphone_panel_is_shown_only_when_option_is_enabled(self) -> None:
        app = BizneoRecorderApp(
            self.root,
            FakeClient(),
            FakeRecorder(),
            chrome_finder=lambda: ChromeProcess(321, Path("chrome.exe")),
        )

        app.include_microphone_var.set(True)
        app._microphone_option_changed()
        self.root.update_idletasks()

        self.assertEqual(app.microphone_panel.winfo_manager(), "pack")

    def test_capture_source_changes_primary_action_and_help(self) -> None:
        app = BizneoRecorderApp(
            self.root,
            FakeClient(),
            FakeRecorder(),
            chrome_finder=lambda: ChromeProcess(321, Path("chrome.exe")),
        )

        app.capture_mode_var.set("Pestaña de Chrome")
        app._capture_mode_changed()
        self.root.update_idletasks()

        self.assertEqual(app.record_button.text, "Elegir pestaña y grabar")
        self.assertIn("Compartir también el audio", app.capture_help_var.get())
        self.assertIn("pestaña", app.status_var.get())
        self.assertTrue(app.capture_mode_cards["Pestaña de Chrome"].selected)

    def test_output_folder_can_be_changed_before_recording(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            selected = Path(directory) / "Grabaciones RRHH"
            app = BizneoRecorderApp(
                self.root,
                FakeClient(),
                FakeRecorder(),
                chrome_finder=lambda: ChromeProcess(321, Path("chrome.exe")),
                directory_chooser=lambda **_kwargs: str(selected),
            )

            app.choose_output_folder()

            self.assertEqual(app.output_dir, selected)
            self.assertIn("Grabaciones RRHH", app.output_path_var.get())


if __name__ == "__main__":
    unittest.main()
