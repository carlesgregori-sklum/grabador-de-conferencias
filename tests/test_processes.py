from __future__ import annotations

import unittest

from bizneo_recorder.processes import ProcessInfo, select_chrome_root


class ChromeProcessSelectionTests(unittest.TestCase):
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
