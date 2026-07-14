from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from bizneo_recorder.ffmpeg import FFmpegClient  # noqa: E402
from bizneo_recorder.models import RecordingConfig  # noqa: E402
from bizneo_recorder.recorder import Recorder  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seconds", type=float, default=3.0)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    client = FFmpegClient(args.ffmpeg)
    microphones = client.list_microphones()
    if not microphones:
        print("No microphone was detected.", file=sys.stderr)
        return 1

    recorder = Recorder(client)
    final_path = recorder.start(
        RecordingConfig(
            microphones[0],
            args.output,
            width=args.width,
            height=args.height,
            fps=args.fps,
        )
    )
    print(f"Recording with: {microphones[0].name}")
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

