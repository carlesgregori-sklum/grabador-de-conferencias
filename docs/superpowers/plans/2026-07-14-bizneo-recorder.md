# Bizneo Recorder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and package a portable Windows application that records the 1920×1080 primary display and one selected microphone to a local MP4.

**Architecture:** A small Python/Tkinter application delegates capture and encoding to a bundled FFmpeg executable. Pure command construction and parsing stay separate from the recorder process lifecycle and UI so the critical behavior is unit-testable.

**Tech Stack:** Python 3.13, standard-library Tkinter and unittest, FFmpeg `gdigrab`/`dshow`, PyInstaller, PowerShell build automation.

## Global Constraints

- Target Windows 11 x64 with no runtime installation required.
- Record the complete primary display at 1920×1080 and 30 fps.
- Capture only the selected microphone; never configure a desktop/system-audio input.
- Write timestamped MP4 files beneath `Videos\Bizneo Recorder`.
- Keep all processing local and retain a recoverable `.part.mp4` on an abnormal FFmpeg exit.
- Keep the project root limited to startup, configuration and overview files.

---

### Task 1: Recording configuration and output paths

**Files:**
- Create: `src/bizneo_recorder/__init__.py`
- Create: `src/bizneo_recorder/models.py`
- Create: `tests/test_models.py`
- Create: `pyproject.toml`

**Interfaces:**
- Produces: `Microphone(name: str, alternative_name: str | None)` and `RecordingConfig(microphone, output_dir, width=1920, height=1080, fps=30)`.
- Produces: `RecordingConfig.next_paths(now: datetime | None = None) -> tuple[Path, Path]` returning final and `.part.mp4` paths.

- [ ] **Step 1: Write failing model tests**

```python
def test_next_paths_uses_timestamp_and_part_suffix(tmp_path):
    config = RecordingConfig(Microphone("Mic"), tmp_path)
    final, working = config.next_paths(datetime(2026, 7, 14, 15, 30, 10))
    assert final.name == "Bizneo-2026-07-14-153010.mp4"
    assert working.name == "Bizneo-2026-07-14-153010.part.mp4"

def test_config_rejects_empty_microphone(tmp_path):
    with self.assertRaises(ValueError):
        RecordingConfig(Microphone(""), tmp_path)
```

- [ ] **Step 2: Run tests and confirm missing-module failure**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL because `bizneo_recorder.models` does not exist.

- [ ] **Step 3: Implement immutable value objects and unique path generation**

```python
@dataclass(frozen=True, slots=True)
class Microphone:
    name: str
    alternative_name: str | None = None

@dataclass(frozen=True, slots=True)
class RecordingConfig:
    microphone: Microphone
    output_dir: Path
    width: int = 1920
    height: int = 1080
    fps: int = 30

    def next_paths(self, now: datetime | None = None) -> tuple[Path, Path]:
        stamp = (now or datetime.now()).strftime("%Y-%m-%d-%H%M%S")
        final = self.output_dir / f"Bizneo-{stamp}.mp4"
        counter = 2
        while final.exists() or final.with_suffix(".part.mp4").exists():
            final = self.output_dir / f"Bizneo-{stamp}-{counter}.mp4"
            counter += 1
        return final, final.with_suffix(".part.mp4")
```

- [ ] **Step 4: Run tests and commit**

Run: `python -m unittest discover -s tests -v`
Expected: PASS.

Commit: `git commit -am "feat: add recording configuration"` after adding new files.

### Task 2: FFmpeg microphone discovery and command construction

**Files:**
- Create: `src/bizneo_recorder/ffmpeg.py`
- Create: `tests/test_ffmpeg.py`

**Interfaces:**
- Produces: `parse_dshow_audio_devices(text: str) -> list[Microphone]`.
- Produces: `FFmpegClient(executable: Path)`, `.list_microphones()`, `.build_record_command(config, working_path)` and `.self_test()`.

- [ ] **Step 1: Write failing parser and command tests**

```python
def test_parse_audio_devices_excludes_video_devices():
    text = '"Integrated Camera" (video)\n"Microphone Array" (audio)\nAlternative name "@device_cm_..."'
    assert parse_dshow_audio_devices(text) == [Microphone("Microphone Array", "@device_cm_...")]

def test_record_command_has_desktop_and_only_selected_microphone(tmp_path):
    config = RecordingConfig(Microphone("Microphone Array"), tmp_path)
    command = FFmpegClient(Path("ffmpeg.exe")).build_record_command(config, tmp_path / "x.part.mp4")
    assert "desktop" in command
    assert 'audio=Microphone Array' in command
    assert "Stereo Mix" not in command
    assert "1920:1080" in " ".join(command)
```

- [ ] **Step 2: Run the focused tests and confirm import failure**

Run: `python -m unittest tests.test_ffmpeg -v`
Expected: FAIL because `bizneo_recorder.ffmpeg` does not exist.

- [ ] **Step 3: Implement robust DirectShow parsing and deterministic arguments**

Use `subprocess.run([ffmpeg, "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"])`, parse quoted `(audio)` lines and their optional following alternative-name line, de-duplicate by display name, and build a `gdigrab` plus `dshow` command using H.264/AAC and a fixed 1920×1080 scale/pad filter.

- [ ] **Step 4: Run tests and commit**

Run: `python -m unittest discover -s tests -v`
Expected: PASS.

Commit: `git commit -am "feat: add FFmpeg capture integration"` after adding new files.

### Task 3: Safe recorder lifecycle

**Files:**
- Create: `src/bizneo_recorder/recorder.py`
- Create: `tests/test_recorder.py`

**Interfaces:**
- Produces: `RecorderState` enum with `IDLE`, `RECORDING`, `STOPPING`.
- Produces: `Recorder.start(config) -> Path`, `Recorder.stop(timeout=15.0) -> Path`, `Recorder.poll() -> int | None`, `Recorder.last_error -> str`.

- [ ] **Step 1: Write failing state and finalization tests using a fake process factory**

```python
def test_start_transitions_to_recording_and_returns_final_path(tmp_path):
    recorder = Recorder(fake_client, process_factory)
    path = recorder.start(config)
    assert recorder.state is RecorderState.RECORDING
    assert path.suffix == ".mp4"

def test_successful_stop_sends_q_and_promotes_working_file(tmp_path):
    final = recorder.start(config)
    recorder.working_path.write_bytes(b"mp4")
    assert recorder.stop() == final
    assert final.read_bytes() == b"mp4"
    assert fake_process.stdin.writes == ["q\n"]
```

- [ ] **Step 2: Run tests and confirm import failure**

Run: `python -m unittest tests.test_recorder -v`
Expected: FAIL because `bizneo_recorder.recorder` does not exist.

- [ ] **Step 3: Implement one-process state machine**

Start FFmpeg with redirected stdin/stderr and `CREATE_NO_WINDOW`; send `q` for graceful stop; kill only after timeout; rename the working file with `Path.replace` only for exit code 0; retain diagnostics and the working file otherwise.

- [ ] **Step 4: Run tests and commit**

Run: `python -m unittest discover -s tests -v`
Expected: PASS.

Commit: `git commit -am "feat: add safe recorder lifecycle"` after adding new files.

### Task 4: Windows user interface and self-test

**Files:**
- Create: `src/bizneo_recorder/app.py`
- Create: `src/bizneo_recorder/main.py`
- Create: `tests/test_main.py`

**Interfaces:**
- Produces: `resource_path(relative: str) -> Path` resolving source and frozen-app paths.
- Produces: `run_self_test(client: FFmpegClient) -> int`.
- Produces: `BizneoRecorderApp(root, client, recorder)` and `main(argv=None) -> int`.

- [ ] **Step 1: Write failing resource-path and self-test tests**

```python
def test_resource_path_uses_executable_directory_when_frozen(self):
    with patch.object(sys, "frozen", True, create=True), \
         patch.object(sys, "executable", str(self.tmp_path / "Bizneo Recorder.exe")):
        self.assertEqual(resource_path("tools/ffmpeg.exe"), self.tmp_path / "tools/ffmpeg.exe")

def test_self_test_fails_when_no_microphone_is_found():
    assert run_self_test(ClientWithNoMicrophones()) == 1
```

- [ ] **Step 2: Run tests and confirm import failure**

Run: `python -m unittest tests.test_main -v`
Expected: FAIL because `bizneo_recorder.main` does not exist.

- [ ] **Step 3: Implement the compact Tkinter workflow**

Create a single accessible window with microphone combobox, refresh button, output-folder label, primary start/stop button, elapsed timer, status text and open-folder button. Run blocking discovery/start/stop operations off the Tk thread, marshal results through `after`, disable invalid actions, and confirm close while recording.

- [ ] **Step 4: Implement `--self-test` and run all tests**

Run: `python -m unittest discover -s tests -v`
Expected: PASS.

Commit: `git commit -am "feat: add recorder interface and diagnostics"` after adding new files.

### Task 5: Portable build, documentation and end-to-end verification

**Files:**
- Create: `scripts/build-portable.ps1`
- Create: `scripts/verify-recording.ps1`
- Create: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/usage.md`
- Create: `.gitignore`

**Interfaces:**
- Produces: `outputs/Bizneo-Recorder-Portable.zip` containing `Bizneo Recorder.exe`, `tools/ffmpeg.exe`, FFmpeg license and `LLEGEIX-ME.txt`.

- [ ] **Step 1: Add a failing package-layout test to the build script**

The script must stop if the executable, FFmpeg binary, license or guide is absent before archive creation.

- [ ] **Step 2: Download and verify the FFmpeg archive, install build-only Python tools, and build**

Use the stable Gyan FFmpeg essentials URL over HTTPS, record SHA-256 locally, copy only the required runtime binary and license, install PyInstaller into `work/build-venv`, and build the windowed one-file launcher. Do not place caches or build products in the project root.

Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1`
Expected: archive created beneath `outputs` and all required layout assertions pass.

- [ ] **Step 3: Write usage and architecture documentation**

Document copy-and-run operation, microphone permission troubleshooting, output location, graceful stop, limitations, modules, data flow, folder tree, build commands and verification commands. Keep `docs/architecture.md` aligned with the actual structure.

- [ ] **Step 4: Run clean automated verification**

Run: `python -m unittest discover -s tests -v`
Expected: all tests PASS.

Run: `& 'outputs\Bizneo Recorder\Bizneo Recorder.exe' --self-test`
Expected: FFmpeg available, H.264 encoder available and at least one microphone listed.

- [ ] **Step 5: Record and probe a short end-to-end sample**

Start a three-second screen-plus-selected-microphone capture, stop with `q`, and inspect it with FFmpeg. Assert one H.264 1920×1080 video stream, one AAC audio stream and a duration greater than zero.

- [ ] **Step 6: Review, commit and archive**

Run: `git status --short` and inspect the complete diff. Commit source, tests, scripts and docs without committing downloaded tools or build caches.

Commit: `git commit -m "feat: deliver portable Bizneo screen recorder"`.
