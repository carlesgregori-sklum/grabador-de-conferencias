from __future__ import annotations

import ctypes
from collections import defaultdict
from collections.abc import Iterable
from ctypes import wintypes
from dataclasses import dataclass


class ProcessDiscoveryError(RuntimeError):
    """Raised when Windows cannot enumerate the active processes."""


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    pid: int
    parent_pid: int
    name: str


class _ProcessEntry32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def select_chrome_root(processes: Iterable[ProcessInfo]) -> int | None:
    """Return the deterministic root PID of the largest Chrome process tree."""

    chrome = {
        item.pid: item
        for item in processes
        if item.name.casefold() == "chrome.exe" and item.pid > 0
    }
    roots = [item for item in chrome.values() if item.parent_pid not in chrome]
    if not roots:
        return None

    children: dict[int, list[int]] = defaultdict(list)
    for item in chrome.values():
        children[item.parent_pid].append(item.pid)

    def tree_size(pid: int, ancestors: frozenset[int] = frozenset()) -> int:
        if pid in ancestors:
            return 0
        next_ancestors = ancestors | {pid}
        return 1 + sum(
            tree_size(child, next_ancestors) for child in children.get(pid, ())
        )

    return min(roots, key=lambda item: (-tree_size(item.pid), item.pid)).pid


def enumerate_processes() -> list[ProcessInfo]:
    """Enumerate processes with Tool Help without spawning a shell command."""

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_snapshot = kernel32.CreateToolhelp32Snapshot
    create_snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    create_snapshot.restype = wintypes.HANDLE
    process_first = kernel32.Process32FirstW
    process_first.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ProcessEntry32W)]
    process_first.restype = wintypes.BOOL
    process_next = kernel32.Process32NextW
    process_next.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ProcessEntry32W)]
    process_next.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    snapshot = create_snapshot(0x00000002, 0)
    if snapshot == wintypes.HANDLE(-1).value:
        raise ProcessDiscoveryError(
            f"Windows no ha pogut enumerar els processos ({ctypes.get_last_error()})."
        )

    processes: list[ProcessInfo] = []
    try:
        entry = _ProcessEntry32W()
        entry.dwSize = ctypes.sizeof(entry)
        if not process_first(snapshot, ctypes.byref(entry)):
            error = ctypes.get_last_error()
            raise ProcessDiscoveryError(
                f"Windows no ha pogut llegir els processos ({error})."
            )
        while True:
            processes.append(
                ProcessInfo(
                    int(entry.th32ProcessID),
                    int(entry.th32ParentProcessID),
                    entry.szExeFile,
                )
            )
            if not process_next(snapshot, ctypes.byref(entry)):
                break
    finally:
        close_handle(snapshot)
    return processes


def find_chrome_root() -> int | None:
    return select_chrome_root(enumerate_processes())
