from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from bizneo_recorder.chrome_audio import ChromeAudioClient  # noqa: E402
from bizneo_recorder.ffmpeg import FFmpegClient  # noqa: E402
from bizneo_recorder.models import RecordingConfig  # noqa: E402
from bizneo_recorder.processes import find_chrome_root  # noqa: E402
from bizneo_recorder.recorder import Recorder  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", required=True, type=Path)
    parser.add_argument("--chrome-audio-helper", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--include-microphone", action="store_true")
    args = parser.parse_args()

    chrome_process_id = find_chrome_root()
    if chrome_process_id is None:
        print("Chrome must be open before the smoke recording.", file=sys.stderr)
        return 1

    client = FFmpegClient(args.ffmpeg)
    microphone = None
    if args.include_microphone:
        microphones = client.list_microphones()
        if not microphones:
            print("No microphone was detected.", file=sys.stderr)
            return 1
        microphone = microphones[0]

    recorder = Recorder(client, ChromeAudioClient(args.chrome_audio_helper))
    final_path = recorder.start(
        RecordingConfig(
            args.output,
            chrome_process_id,
            microphone=microphone,
            width=args.width,
            height=args.height,
            fps=args.fps,
        )
    )
    print(f"Chrome root PID: {chrome_process_id}")
    print(f"Microphone: {microphone.name if microphone else 'disabled'}")
    print(f"Profile: {args.width}x{args.height} at {args.fps} FPS")
    time.sleep(max(1.0, args.seconds))
    saved_path = recorder.stop()
    if saved_path != final_path:
        print("Unexpected output path.", file=sys.stderr)
        return 1
    print(saved_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
