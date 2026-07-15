from __future__ import annotations

import tkinter as tk
import unittest

from bizneo_recorder.app import BizneoRecorderApp
from bizneo_recorder.models import Microphone
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
            chrome_finder=lambda: 321,
        )
        self.root.update_idletasks()

        self.assertEqual(self.root.title(), "Conference Recorder")
        self.assertFalse(app.include_microphone_var.get())
        self.assertEqual(app.microphone_panel.winfo_manager(), "")
        self.assertEqual(str(app.record_button.cget("state")), "normal")
        self.assertEqual(app.chrome_process_id, 321)

    def test_microphone_panel_is_shown_only_when_option_is_enabled(self) -> None:
        app = BizneoRecorderApp(
            self.root,
            FakeClient(),
            FakeRecorder(),
            chrome_finder=lambda: 321,
        )

        app.include_microphone_var.set(True)
        app._microphone_option_changed()
        self.root.update_idletasks()

        self.assertEqual(app.microphone_panel.winfo_manager(), "pack")


if __name__ == "__main__":
    unittest.main()
