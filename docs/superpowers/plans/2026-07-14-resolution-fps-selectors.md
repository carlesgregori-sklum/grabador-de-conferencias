# Resolution and FPS Selectors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add independent 720p/1080p and 30/60 FPS selectors to Bizneo Recorder and ship a newly verified portable package.

**Architecture:** Supported values live in `models.py` as immutable presets and validation helpers. The Tkinter UI resolves its two read-only selections into the existing `RecordingConfig`, while FFmpeg continues to consume only numeric width, height and FPS values.

**Tech Stack:** Python 3.13, Tkinter, unittest, FFmpeg, PowerShell, PyInstaller 6.21.0.

## Global Constraints

- Resolution choices are exactly `HD 720p` (1280×720) and `Full HD 1080p` (1920×1080).
- Frame-rate choices are exactly `30 FPS` and `60 FPS`.
- Default is `Full HD 1080p · 30 FPS`.
- All four combinations are valid.
- Quality selectors are locked during start, recording and finalization.
- Microphone-only audio, MP4 output, naming and output folder remain unchanged.
- Documentation in `docs`, including `docs/architecture.md`, must match the implementation.

---

### Task 1: Supported recording quality model

**Files:**
- Modify: `src/bizneo_recorder/models.py`
- Modify: `tests/test_models.py`

**Interfaces:**
- Produces: `ResolutionPreset(label: str, width: int, height: int)`.
- Produces: `RESOLUTION_PRESETS: tuple[ResolutionPreset, ...]` and `SUPPORTED_FPS: tuple[int, ...]`.
- Produces: `get_resolution_preset(label: str) -> ResolutionPreset` and `parse_fps(label: str) -> int`.

- [ ] **Step 1: Write failing preset and validation tests**

```python
def test_supported_resolution_presets_are_720p_and_1080p(self):
    self.assertEqual(
        [(item.label, item.width, item.height) for item in RESOLUTION_PRESETS],
        [("HD 720p", 1280, 720), ("Full HD 1080p", 1920, 1080)],
    )

def test_parse_fps_accepts_only_supported_labels(self):
    self.assertEqual(parse_fps("30 FPS"), 30)
    self.assertEqual(parse_fps("60 FPS"), 60)
    with self.assertRaises(ValueError):
        parse_fps("25 FPS")
```

- [ ] **Step 2: Run the focused tests and confirm import failure**

Run: `python -m unittest tests.test_models -v`
Expected: FAIL because the quality symbols do not exist.

- [ ] **Step 3: Implement immutable presets and strict helpers**

```python
@dataclass(frozen=True, slots=True)
class ResolutionPreset:
    label: str
    width: int
    height: int

RESOLUTION_PRESETS = (
    ResolutionPreset("HD 720p", 1280, 720),
    ResolutionPreset("Full HD 1080p", 1920, 1080),
)
SUPPORTED_FPS = (30, 60)

def get_resolution_preset(label: str) -> ResolutionPreset:
    return next(item for item in RESOLUTION_PRESETS if item.label == label)

def parse_fps(label: str) -> int:
    value = int(label.removesuffix(" FPS"))
    if value not in SUPPORTED_FPS:
        raise ValueError("unsupported frame rate")
    return value
```

Convert lookup failures into clear `ValueError` messages rather than leaking `StopIteration` or accepting malformed labels.

- [ ] **Step 4: Run all tests and commit**

Run: `python -m unittest discover -s tests -t . -v`
Expected: all tests PASS.

Commit: `git commit -am "feat: add recording quality presets"`.

### Task 2: Quality selectors and FFmpeg combinations

**Files:**
- Modify: `src/bizneo_recorder/app.py`
- Modify: `tests/test_ffmpeg.py`
- Modify: `tests/test_main.py`

**Interfaces:**
- Consumes: `RESOLUTION_PRESETS`, `SUPPORTED_FPS`, `get_resolution_preset()` and `parse_fps()`.
- Produces: `build_recording_config(microphone, output_dir, resolution_label, fps_label) -> RecordingConfig`.
- Produces: two read-only comboboxes whose selected values populate `RecordingConfig.width`, `.height` and `.fps`.

- [ ] **Step 1: Write failing FFmpeg combination tests**

```python
def test_build_recording_config_supports_every_quality_combination(self):
    for resolution, expected_size in (
        ("HD 720p", (1280, 720)),
        ("Full HD 1080p", (1920, 1080)),
    ):
        for fps_label, expected_fps in (("30 FPS", 30), ("60 FPS", 60)):
            config = build_recording_config(
                Microphone("Mic"), output_dir, resolution, fps_label
            )
            self.assertEqual((config.width, config.height), expected_size)
            self.assertEqual(config.fps, expected_fps)

def test_record_command_uses_selected_720p_60_profile(self):
    config = RecordingConfig(Microphone("Mic"), output_dir, 1280, 720, 60)
    command = client.build_record_command(config, output_dir / "x.part.mp4")
    self.assertIn("1280:720", " ".join(command))
    self.assertGreaterEqual(command.count("60"), 2)
```

- [ ] **Step 2: Run the focused test and confirm it fails before the test helper is complete**

Run: `python -m unittest tests.test_main -v`
Expected: FAIL because `build_recording_config` does not exist.

- [ ] **Step 3: Add the two selectors and apply their values on start**

Implement `build_recording_config` using the strict model helpers. Create `resolution_var` defaulting to `Full HD 1080p` and `fps_var` defaulting to `30 FPS`. Add labelled read-only comboboxes under **Qualitat del vídeo**, plus the helper `60 FPS crea fitxers més grans i exigeix més a l'equip.` Resolve the values immediately before `RecordingConfig` creation.

Use a single `_set_quality_controls_state(state: str)` helper from refresh/start/stop paths so both selectors are `disabled` while busy and `readonly` while idle.

- [ ] **Step 4: Run tests and commit**

Run: `python -m unittest discover -s tests -t . -v`
Expected: all tests PASS.

Run: `python -m compileall -q src tests`
Expected: exit code 0.

Commit: `git commit -am "feat: add resolution and FPS selectors"`.

### Task 3: Verification scripts, documentation and portable release

**Files:**
- Modify: `scripts/smoke-recording.py`
- Modify: `scripts/verify-recording.ps1`
- Modify: `docs/usage.md`
- Modify: `docs/portable-readme.txt`
- Modify: `docs/architecture.md`
- Modify: `docs/verification.md`

**Interfaces:**
- `smoke-recording.py` accepts `--width`, `--height` and `--fps`.
- `verify-recording.ps1` accepts `ExpectedWidth`, `ExpectedHeight` and `ExpectedFps` parameters.

- [ ] **Step 1: Extend smoke and probe inputs**

Pass the three CLI values into `RecordingConfig`. In PowerShell, validate width, height, codec names and rounded `avg_frame_rate` against the expected values, with defaults 1920, 1080 and 30 for backward compatibility.

- [ ] **Step 2: Update all affected documentation**

Document both selectors, defaults, the 60 FPS size/performance trade-off, four combinations, changed data flow and new verification commands. Keep the architecture tree unchanged because no files are added.

- [ ] **Step 3: Run static and automated checks**

Run: `python -m unittest discover -s tests -t . -v`
Expected: all tests PASS.

Run: `ruff check src tests scripts/launcher.py scripts/smoke-recording.py`
Expected: `All checks passed!`.

Parse every `scripts/*.ps1` file with `System.Management.Automation.Language.Parser`.
Expected: no syntax errors.

- [ ] **Step 4: Build and validate the portable package**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1`
Expected: package and ZIP created.

Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1 -ValidateOnly`
Expected: portable layout complete.

Run packaged `Bizneo Recorder.exe --self-test` with `Start-Process -Wait -PassThru`.
Expected: exit code 0.

- [ ] **Step 5: Record the boundary profiles and probe them**

Record short samples at 1920×1080/30 and 1280×720/60 using the bundled FFmpeg. Probe each with the updated PowerShell verifier, confirm H.264 video and AAC audio, then remove the screen-and-voice samples.

- [ ] **Step 6: Commit and integrate**

Run: `git diff --check`, inspect `git status --short`, commit the scripts and docs, merge the verified feature branch to `main`, rerun the full test suite and copy the rebuilt folder and ZIP to the root `outputs` directory.
