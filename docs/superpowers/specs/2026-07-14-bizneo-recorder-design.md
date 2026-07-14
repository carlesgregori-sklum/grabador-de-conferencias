# Bizneo Recorder — Design Specification

## Goal

Provide a small portable Windows application that records the complete primary display and the user's selected microphone into a high-definition MP4 video suitable for explaining a Bizneo workflow to Santiago.

## Confirmed scope

- Windows 11, 64-bit.
- Primary display capture at 1920×1080 and 30 frames per second.
- Microphone audio only; desktop/system audio is excluded.
- Portable operation without installation.
- Local-only processing with no uploads or network activity while recording.
- Automatic MP4 output under `Videos\Bizneo Recorder` with a timestamped filename.

Webcam capture, editing, annotations, multi-monitor selection and system-audio capture are deliberately outside this first version.

## User experience

The application opens as a compact single window named **Bizneo Recorder**. It lists available microphones, shows the output folder, and exposes one primary action. Before recording, the user selects a microphone and presses **Començar gravació**. During recording, the UI displays a red recording state and elapsed time. Pressing **Finalitzar i guardar** closes the media stream cleanly, promotes the temporary file to the final MP4 name, and offers a button to open its folder.

The app prevents accidental window closure while recording. If a recording cannot start or finalize, it shows an actionable Valencian error message and preserves any recoverable temporary file.

## Architecture

The portable distribution contains a PyInstaller-built Windows executable and a sidecar FFmpeg binary. Keeping FFmpeg outside the executable avoids a long one-file extraction delay while retaining copy-and-run portability.

The Python source is split into focused modules:

- `models.py`: immutable recording configuration and microphone value objects.
- `ffmpeg.py`: DirectShow microphone discovery and FFmpeg argument construction.
- `recorder.py`: process lifecycle, safe stop/finalization and recording state.
- `app.py`: Tkinter interface, timer and user-facing error handling.
- `main.py`: executable entry point and command-line self-test.

The UI does not know FFmpeg command details. It supplies a validated configuration to the recorder, receives state transitions, and updates controls accordingly. The recorder writes to a `.part.mp4` working file and renames it atomically only after FFmpeg exits successfully.

## Recording profile

- Video source: FFmpeg `gdigrab`, complete primary desktop, cursor included.
- Audio source: FFmpeg `dshow`, selected microphone only.
- Output: H.264 video (`libx264`, `veryfast`, CRF 18, `yuv420p`) and AAC audio (48 kHz, 192 kb/s).
- Canvas: fixed 1920×1080 with aspect-preserving scale and padding if the source resolution differs.
- Container: MP4 with fast-start metadata.

## Error handling

- Missing FFmpeg: block recording and explain that the portable folder is incomplete.
- No microphone: disable recording and provide a refresh action.
- Invalid/unavailable microphone: keep the window usable and ask the user to refresh or choose another device.
- Existing output or unwritable folder: generate a unique name or report the filesystem error before starting.
- FFmpeg start/runtime failure: show a concise excerpt of diagnostic output and retain the temporary file when it may be recoverable.
- Application close during recording: request confirmation and perform the same graceful stop path.

## Verification strategy

- Unit tests cover DirectShow device parsing, timestamped paths, FFmpeg argument construction and recorder state transitions.
- A command-line `--self-test` validates the packaged FFmpeg path, encoder availability, screen-capture input and microphone discovery.
- The release build is started as a smoke test.
- A short local recording validates that the produced MP4 contains one 1920×1080 H.264 video stream and one AAC audio stream, with no system-audio input configured.

## Distribution and maintenance

The user-facing deliverable is a ZIP archive in `outputs` containing the executable, `tools\ffmpeg.exe`, the relevant FFmpeg license file and a concise usage guide. Source, tests and full maintenance documentation remain in the project folders. No runtime installer or administrator rights are required.

