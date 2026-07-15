from __future__ import annotations

import tkinter as tk
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

    def test_initial_state_is_chrome_only_and_ready(self) -> None:
        app = BizneoRecorderApp(
            self.root,
            FakeClient(),
            FakeRecorder(),
            chrome_finder=lambda: ChromeProcess(321, Path("chrome.exe")),
        )
        self.root.update_idletasks()

        self.assertEqual(self.root.title(), "Conference Recorder")
        self.assertFalse(app.include_microphone_var.get())
        self.assertEqual(app.microphone_panel.winfo_manager(), "")
        self.assertEqual(str(app.record_button.cget("state")), "normal")
        self.assertEqual(app.chrome_process_id, 321)
        self.assertEqual(app.capture_mode_var.get(), "Tota la pantalla principal")
        self.assertEqual(len(app.capture_mode_buttons), len(CAPTURE_MODE_LABELS))

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

        app.capture_mode_var.set("Una pestanya de Chrome")
        app._capture_mode_changed()
        self.root.update_idletasks()

        self.assertEqual(app.record_button.cget("text"), "Triar pestanya i gravar")
        self.assertIn("Compartir també l’àudio", app.capture_help_var.get())
        self.assertIn("pestanya", app.status_var.get())


if __name__ == "__main__":
    unittest.main()
