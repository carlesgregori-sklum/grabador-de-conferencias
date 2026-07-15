from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from bizneo_recorder.processes import (
    ChromeProcess,
    ProcessInfo,
    find_chrome,
    select_chrome_root,
)


class ChromeProcessSelectionTests(unittest.TestCase):
    def test_chrome_process_contains_root_and_executable(self) -> None:
        chrome = ChromeProcess(
            321,
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        )

        self.assertEqual(chrome.pid, 321)
        self.assertEqual(chrome.executable.name, "chrome.exe")

    def test_find_chrome_returns_selected_root_and_executable(self) -> None:
        processes = [
            ProcessInfo(100, 10, "chrome.exe"),
            ProcessInfo(101, 100, "chrome.exe"),
        ]
        executable = Path(r"C:\Chrome\chrome.exe")
        with (
            patch(
                "bizneo_recorder.processes.enumerate_processes",
                return_value=processes,
            ),
            patch(
                "bizneo_recorder.processes.query_process_executable",
                return_value=executable,
            ) as query,
        ):
            chrome = find_chrome()

        self.assertEqual(chrome, ChromeProcess(100, executable))
        query.assert_called_once_with(100)

    def test_selects_root_of_largest_chrome_tree(self) -> None:
        processes = [
            ProcessInfo(100, 10, "chrome.exe"),
            ProcessInfo(101, 100, "chrome.exe"),
            ProcessInfo(102, 100, "chrome.exe"),
            ProcessInfo(200, 20, "chrome.exe"),
            ProcessInfo(201, 200, "chrome.exe"),
            ProcessInfo(300, 10, "notepad.exe"),
        ]

        self.assertEqual(select_chrome_root(processes), 100)

    def test_returns_none_without_chrome(self) -> None:
        self.assertIsNone(select_chrome_root([ProcessInfo(1, 0, "explorer.exe")]))

    def test_name_matching_is_case_insensitive(self) -> None:
        self.assertEqual(select_chrome_root([ProcessInfo(44, 1, "CHROME.EXE")]), 44)

    def test_tie_breaks_on_lowest_pid(self) -> None:
        processes = [
            ProcessInfo(200, 1, "chrome.exe"),
            ProcessInfo(100, 1, "chrome.exe"),
        ]

        self.assertEqual(select_chrome_root(processes), 100)


if __name__ == "__main__":
    unittest.main()
