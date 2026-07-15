from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import TextIO

from .app import BizneoRecorderApp
from .browser_capture import BrowserCaptureBridge
from .chrome_audio import ChromeAudioClient
from .ffmpeg import FFmpegClient, FFmpegError
from .processes import ProcessDiscoveryError, find_chrome_root
from .models import RecordingConfig, RecordingPaths
from .recorder import Recorder


def resource_path(relative: str) -> Path:
    """Resolve a sidecar resource beside the executable or project root."""

    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).resolve().parents[2]
    return base_dir / Path(relative)


def load_browser_capture_page() -> str:
    return (
        resources.files("bizneo_recorder")
        .joinpath("assets", "browser_capture.html")
        .read_text(encoding="utf-8")
    )


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
        "H.264: correcto" if diagnostic.encoder_available else "H.264: no disponible",
        file=output,
    )
    chrome_diagnostic = chrome_audio.diagnose()
    if chrome_diagnostic.supported:
        print("Audio de Chrome: correcto", file=output)
    else:
        print(f"Audio de Chrome: error — {chrome_diagnostic.detail}", file=output)

    try:
        chrome_process_id = chrome_finder()
    except ProcessDiscoveryError as error:
        print(f"Chrome: error — {error}", file=output)
    else:
        print(
            "Chrome: detectado" if chrome_process_id else "Chrome: no está abierto",
            file=output,
        )

    if diagnostic.microphones:
        print("Micrófonos opcionales detectados:", file=output)
        for microphone in diagnostic.microphones:
            print(f"- {microphone.name}", file=output)
    else:
        print("Micrófonos: no se ha detectado ningún micrófono (opcional)", file=output)

    return 0 if diagnostic.encoder_available and chrome_diagnostic.supported else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Grabador portable de pantalla y audio de Chrome"
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="comprueba FFmpeg y el audio de Chrome sin abrir la ventana",
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
    browser_capture_page = load_browser_capture_page()

    def make_browser_capture(
        config: RecordingConfig,
        paths: RecordingPaths,
    ) -> BrowserCaptureBridge:
        return BrowserCaptureBridge(
            browser_capture_page,
            config.capture_mode,
            paths.browser_capture,
            config.fps,
        )

    recorder = Recorder(
        client,
        chrome_audio,
        browser_capture_factory=make_browser_capture,
    )
    BizneoRecorderApp(root, client, recorder)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
