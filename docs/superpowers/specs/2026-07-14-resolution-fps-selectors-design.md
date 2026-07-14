# Resolution and FPS Selectors — Design Specification

## Goal

Allow the user to choose video resolution and frame rate independently before starting a Bizneo Recorder capture, while preserving the existing simple workflow and safe MP4 finalization.

## Confirmed scope

- Resolution selector with exactly `HD 720p` (1280×720) and `Full HD 1080p` (1920×1080).
- Frame-rate selector with exactly `30 FPS` and `60 FPS`.
- Default profile remains `Full HD 1080p · 30 FPS`.
- All four combinations are valid.
- The chosen values apply to the next recording and remain locked while recording.
- Existing microphone-only audio, MP4 output, naming and output folder remain unchanged.

Custom dimensions, frame rates other than 30/60, bitrate controls, system audio and multi-monitor selection remain outside scope.

## User experience

The existing recording card gains a **Qualitat del vídeo** section beneath the microphone selector. Two read-only comboboxes sit side by side: **Resolució** and **Fluïdesa**. A short helper explains that 60 FPS produces larger files and requires more processing power.

Both selectors are enabled while idle and disabled during start, recording and finalization. After a successful or failed stop, they return to the enabled read-only state. The current selection is retained for a subsequent recording in the same session.

## Architecture

`models.py` becomes the single source of truth for supported resolution presets and frame rates. A small immutable `ResolutionPreset` value object carries label, width and height. Lookup helpers reject unsupported labels or FPS values.

`app.py` owns only the selected display labels. When recording starts, it resolves those labels through the model helpers and creates `RecordingConfig` with the resulting width, height and FPS. `ffmpeg.py` already consumes those numeric values, so no new FFmpeg abstraction is needed.

## Error handling

- Comboboxes are read-only, preventing arbitrary values during normal use.
- Missing or unsupported values block recording with a clear Valencian message.
- Existing microphone and FFmpeg errors continue through the current handling path.
- A 60 FPS helper warning is informational; it does not block capture.

## Verification

- Unit tests cover both presets, supported FPS values and rejection of unsupported selections.
- FFmpeg command tests cover the four resolution/FPS combinations and verify the matching scale and frame-rate arguments.
- Source lint, unit tests, PowerShell syntax and package layout run again.
- The rebuilt executable runs `--self-test` from the final output folder.
- Short real recordings validate at least the default 1080p/30 profile and the most demanding alternative 720p/60 profile with ffprobe.
- Usage, architecture, portable guide and verification documentation are updated with the selectors and their trade-offs.

