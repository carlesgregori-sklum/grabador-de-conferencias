from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from .app import BizneoRecorderApp, format_elapsed
from .ffmpeg import FFmpegClient, FFmpegError
from .recorder import Recorder


def resource_path(relative: str) -> Path:
    """Resolve a sidecar resource beside the executable or project root."""

    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).resolve().parents[2]
    return base_dir / Path(relative)


def run_self_test(client: FFmpegClient, output: TextIO = sys.stdout) -> int:
    """Print actionable runtime diagnostics without opening the UI."""

    try:
        diagnostic = client.diagnose()
    except FFmpegError as error:
        print(f"FFmpeg: error — {error}", file=output)
        return 1

    print(
        "H.264: correcte" if diagnostic.encoder_available else "H.264: no disponible",
        file=output,
    )
    if diagnostic.microphones:
        print("Micròfons detectats:", file=output)
        for microphone in diagnostic.microphones:
            print(f"- {microphone.name}", file=output)
    else:
        print("Micròfons: no s'ha detectat cap micròfon", file=output)

    return 0 if diagnostic.encoder_available and diagnostic.microphones else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gravador portàtil de pantalla i veu")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="comprova FFmpeg i els micròfons sense obrir la finestra",
    )
    args = parser.parse_args(argv)

    client = FFmpegClient(resource_path("tools/ffmpeg.exe"))
    if args.self_test:
        return run_self_test(client)

    import tkinter as tk

    root = tk.Tk()
    recorder = Recorder(client)
    BizneoRecorderApp(root, client, recorder)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
