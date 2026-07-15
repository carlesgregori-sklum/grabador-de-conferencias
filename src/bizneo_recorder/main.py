from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from .app import BizneoRecorderApp
from .chrome_audio import ChromeAudioClient
from .ffmpeg import FFmpegClient, FFmpegError
from .processes import ProcessDiscoveryError, find_chrome_root
from .recorder import Recorder


def resource_path(relative: str) -> Path:
    """Resolve a sidecar resource beside the executable or project root."""

    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).resolve().parents[2]
    return base_dir / Path(relative)


def run_self_test(
    client: FFmpegClient,
    chrome_audio: ChromeAudioClient,
    chrome_finder: Callable[[], int | None] = find_chrome_root,
    output: TextIO = sys.stdout,
) -> int:
    """Print actionable diagnostics without requiring Chrome or a microphone."""

    try:
        diagnostic = client.diagnose()
    except FFmpegError as error:
        print(f"FFmpeg: error — {error}", file=output)
        return 1

    print(
        "H.264: correcte" if diagnostic.encoder_available else "H.264: no disponible",
        file=output,
    )
    chrome_diagnostic = chrome_audio.diagnose()
    if chrome_diagnostic.supported:
        print("Àudio de Chrome: correcte", file=output)
    else:
        print(f"Àudio de Chrome: error — {chrome_diagnostic.detail}", file=output)

    try:
        chrome_process_id = chrome_finder()
    except ProcessDiscoveryError as error:
        print(f"Chrome: error — {error}", file=output)
    else:
        print(
            "Chrome: detectat" if chrome_process_id else "Chrome: no està obert",
            file=output,
        )

    if diagnostic.microphones:
        print("Micròfons opcionals detectats:", file=output)
        for microphone in diagnostic.microphones:
            print(f"- {microphone.name}", file=output)
    else:
        print("Micròfons: no s'ha detectat cap micròfon (opcional)", file=output)

    return 0 if diagnostic.encoder_available and chrome_diagnostic.supported else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gravador portable de pantalla completa i àudio de Chrome"
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="comprova FFmpeg i l'àudio de Chrome sense obrir la finestra",
    )
    args = parser.parse_args(argv)

    client = FFmpegClient(resource_path("tools/ffmpeg.exe"))
    chrome_audio = ChromeAudioClient(
        resource_path("tools/chrome-audio-capture.exe")
    )
    if args.self_test:
        return run_self_test(client, chrome_audio)

    import tkinter as tk

    root = tk.Tk()
    recorder = Recorder(client, chrome_audio)
    BizneoRecorderApp(root, client, recorder)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
