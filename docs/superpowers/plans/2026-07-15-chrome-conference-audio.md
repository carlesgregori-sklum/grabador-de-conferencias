# Chrome Conference Audio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gravar tota la pantalla principal amb l’àudio exclusiu de l’arbre de processos de Chrome i, opcionalment, mesclar el micròfon en un MP4 portable.

**Architecture:** La UI Tkinter i FFmpeg continuen controlant la captura de pantalla i la codificació. Un helper C# adjacent usa Windows Process Loopback per escriure l’àudio de Chrome en WAV; `Recorder` coordina el helper, FFmpeg i una passada final de mux/mescla segura.

**Tech Stack:** Python 3.11+, Tkinter, unittest, ctypes/Tool Help, FFmpeg/ffprobe, C# .NET Framework x64, WASAPI Process Loopback, PowerShell/PyInstaller.

## Global Constraints

- El vídeo captura sempre tota la pantalla principal i el cursor.
- L’àudio base inclou només Chrome i els seus processos descendents, mai tot Windows.
- El micròfon és opcional i està desactivat per defecte.
- Els perfils admesos continuen sent 720p/1080p i 30/60 FPS; 1080p/30 FPS és el valor inicial.
- La build mínima compatible és Windows 10 build 20348.
- La gravació és local, sense xarxa, telemetria ni dispositius virtuals.
- Els artefactes finals viuen en `outputs/`; les descàrregues i proves temporals, en `work/`.
- Cada comportament nou segueix RED → GREEN → REFACTOR i cada tasca acaba amb totes les proves verdes.

---

## File Map

- `src/bizneo_recorder/processes.py`: enumeració de processos i selecció de l’arrel de Chrome.
- `src/bizneo_recorder/models.py`: configuració amb micròfon opcional i conjunt de rutes de sessió.
- `src/bizneo_recorder/chrome_audio.py`: client Python del helper natiu.
- `native/chrome_audio_capture/ChromeAudioCapture.cs`: captura WASAPI per arbre de processos i escriptura WAV.
- `scripts/build-chrome-audio.ps1`: compilació x64 determinista del helper amb `csc.exe`.
- `src/bizneo_recorder/ffmpeg.py`: ordres de captura de pantalla/micròfon i finalització.
- `src/bizneo_recorder/recorder.py`: coordinació dels processos i recuperació.
- `src/bizneo_recorder/app.py`: UI minimalista orientada a conferències.
- `src/bizneo_recorder/main.py`: recursos, diagnòstic i composició de dependències.
- `tests/`: proves unitàries i de contracte del helper.
- `scripts/build-portable.ps1`: paquet `Conference Recorder` amb FFmpeg i helper.
- `docs/`: ús, arquitectura, verificació i guia portable actualitzats.

---

### Task 1: Chrome process discovery and recording session model

**Files:**
- Create: `src/bizneo_recorder/processes.py`
- Modify: `src/bizneo_recorder/models.py`
- Create: `tests/test_processes.py`
- Modify: `tests/test_models.py`

**Interfaces:**
- Produces: `ProcessInfo(pid: int, parent_pid: int, name: str)`.
- Produces: `select_chrome_root(processes: Iterable[ProcessInfo]) -> int | None`.
- Produces: `find_chrome_root() -> int | None`.
- Produces: `RecordingPaths(final, partial, capture, chrome_audio)`.
- Produces: `RecordingConfig(output_dir, chrome_process_id, microphone=None, width=1920, height=1080, fps=30)`.

- [ ] **Step 1: Write failing process-selection tests**

```python
class ChromeProcessSelectionTests(unittest.TestCase):
    def test_selects_root_of_largest_chrome_tree(self) -> None:
        processes = [
            ProcessInfo(100, 10, "chrome.exe"),
            ProcessInfo(101, 100, "chrome.exe"),
            ProcessInfo(102, 100, "chrome.exe"),
            ProcessInfo(200, 20, "chrome.exe"),
            ProcessInfo(201, 200, "chrome.exe"),
            ProcessInfo(300, 10, "notepad.exe"),
        ]
        self.assertEqual(select_chrome_root(processes), 100)

    def test_returns_none_without_chrome(self) -> None:
        self.assertIsNone(select_chrome_root([ProcessInfo(1, 0, "explorer.exe")]))
```

- [ ] **Step 2: Run the new tests and verify RED**

Run: `python -m unittest tests.test_processes -v`

Expected: import failure because `bizneo_recorder.processes` does not exist.

- [ ] **Step 3: Implement deterministic Chrome root discovery**

Implement `ProcessInfo`, a pure `select_chrome_root` that counts Chrome descendants for every Chrome root, and a Windows-only `find_chrome_root` backed by `CreateToolhelp32Snapshot`, `Process32FirstW` and `Process32NextW`. Close the snapshot handle in `finally`; raise `ProcessDiscoveryError` for Win32 failures and return `None` when no `chrome.exe` exists.

```python
@dataclass(frozen=True, slots=True)
class ProcessInfo:
    pid: int
    parent_pid: int
    name: str

def select_chrome_root(processes: Iterable[ProcessInfo]) -> int | None:
    items = list(processes)
    chrome = {item.pid: item for item in items if item.name.casefold() == "chrome.exe"}
    roots = [item for item in chrome.values() if item.parent_pid not in chrome]
    if not roots:
        return None
    children: dict[int, list[int]] = defaultdict(list)
    for item in chrome.values():
        children[item.parent_pid].append(item.pid)
    def size(pid: int) -> int:
        return 1 + sum(size(child) for child in children.get(pid, ()))
    return min(roots, key=lambda item: (-size(item.pid), item.pid)).pid
```

- [ ] **Step 4: Run process tests and verify GREEN**

Run: `python -m unittest tests.test_processes -v`

Expected: both tests pass.

- [ ] **Step 5: Write failing configuration/path tests**

```python
def test_config_allows_chrome_audio_without_microphone(self) -> None:
    config = RecordingConfig(Path("videos"), chrome_process_id=321)
    self.assertIsNone(config.microphone)

def test_session_paths_cover_every_intermediate(self) -> None:
    config = RecordingConfig(Path("videos"), chrome_process_id=321)
    paths = config.next_paths(datetime(2026, 7, 15, 9, 30, 0))
    self.assertEqual(paths.final.name, "Conference-2026-07-15-093000.mp4")
    self.assertEqual(paths.partial.name, "Conference-2026-07-15-093000.part.mp4")
    self.assertEqual(paths.capture.name, "Conference-2026-07-15-093000.capture.mkv")
    self.assertEqual(paths.chrome_audio.name, "Conference-2026-07-15-093000.chrome.wav")
```

- [ ] **Step 6: Run model tests and verify RED**

Run: `python -m unittest tests.test_models -v`

Expected: constructor/signature assertions fail because Chrome PID and `RecordingPaths` are absent.

- [ ] **Step 7: Implement the new immutable model**

Change `RecordingConfig` field order to `output_dir`, `chrome_process_id`, `microphone`, `width`, `height`, `fps`; reject non-positive PIDs and retain current size/FPS validation. Add `RecordingPaths` and make `next_paths` return it, incrementing the suffix when any member exists.

- [ ] **Step 8: Run all Task 1 tests and commit**

Run: `python -m unittest tests.test_processes tests.test_models -v`

Expected: all pass.

```powershell
git add src/bizneo_recorder/processes.py src/bizneo_recorder/models.py tests/test_processes.py tests/test_models.py
git commit -m "feat: discover Chrome and model conference sessions"
```

---

### Task 2: Native Chrome process-loopback helper

**Files:**
- Create: `native/chrome_audio_capture/ChromeAudioCapture.cs`
- Create: `scripts/build-chrome-audio.ps1`
- Create: `tests/test_chrome_audio_helper.py`
- Create: `src/bizneo_recorder/chrome_audio.py`
- Create: `tests/test_chrome_audio.py`

**Interfaces:**
- Helper CLI: `chrome-audio-capture.exe <pid> <wav-path>`; writes `READY` to stdout, accepts `q` on stdin, and returns 0 only after a valid WAV is closed.
- Helper diagnostic: `chrome-audio-capture.exe --self-test` validates build support and returns 0 on build 20348+.
- Produces: `ChromeAudioClient(executable: Path)` with `diagnose()`, `start(pid, path)` and a `ChromeAudioProcess.stop()` lifecycle.

- [ ] **Step 1: Write failing helper build/CLI tests**

The test calls `scripts/build-chrome-audio.ps1 -OutputPath work/test-helper/chrome-audio-capture.exe`, then checks `--self-test`, missing arguments, and a non-positive PID.

```python
def test_helper_self_test_reports_process_loopback_support(self) -> None:
    result = subprocess.run([str(self.helper), "--self-test"], capture_output=True, text=True)
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertIn("Process loopback: supported", result.stdout)

def test_helper_rejects_invalid_pid(self) -> None:
    result = subprocess.run([str(self.helper), "0", "capture.wav"], capture_output=True, text=True)
    self.assertEqual(result.returncode, 2)
    self.assertIn("PID", result.stderr)
```

- [ ] **Step 2: Run helper tests and verify RED**

Run: `python -m unittest tests.test_chrome_audio_helper -v`

Expected: build script/source missing.

- [ ] **Step 3: Implement the helper and compiler script**

`build-chrome-audio.ps1` locates `%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe`, creates only the requested parent directory, and compiles with `/nologo /optimize+ /platform:x64 /target:exe`.

`ChromeAudioCapture.cs` defines the documented COM contracts for `ActivateAudioInterfaceAsync`, `IAudioClient`, `IAudioCaptureClient`, `IActivateAudioInterfaceCompletionHandler`, `IActivateAudioInterfaceAsyncOperation`, `AUDIOCLIENT_ACTIVATION_PARAMS` and `AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS`. Use:

```csharp
const string ProcessLoopbackDevice = "VAD\\Process_Loopback";
const int MinimumBuild = 20348;
const int SampleRate = 44100;
const short Channels = 2;
const short BitsPerSample = 16;
```

Create a `PROPVARIANT` blob for the target PID with `PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE`; initialize shared event-driven loopback, write every received buffer to a provisional WAV after a 44-byte header, write zero bytes for `AUDCLNT_BUFFERFLAGS_SILENT`, and patch RIFF/data sizes on orderly stop. All COM pointers, events, allocated blobs and file handles are released in `finally`/`Dispose`.

- [ ] **Step 4: Run helper tests and verify GREEN**

Run: `python -m unittest tests.test_chrome_audio_helper -v`

Expected: helper builds, self-test passes on build 26200, invalid PID returns 2.

- [ ] **Step 5: Write failing Python client tests**

```python
def test_start_waits_for_ready_line(self) -> None:
    process = FakeProcess(stdout=io.StringIO("READY\n"))
    client = ChromeAudioClient(Path("helper.exe"), process_factory=Factory(process))
    handle = client.start(321, Path("chrome.wav"))
    self.assertEqual(handle.pid, 321)

def test_stop_sends_q_and_requires_zero_exit(self) -> None:
    handle = make_handle(returncode=0)
    handle.stop()
    self.assertEqual(handle.process.stdin.getvalue(), "q\n")
```

- [ ] **Step 6: Run client tests and verify RED**

Run: `python -m unittest tests.test_chrome_audio -v`

Expected: import failure because `chrome_audio.py` does not exist.

- [ ] **Step 7: Implement the Python helper client**

Implement `ChromeAudioError`, `ChromeAudioDiagnostic`, `ChromeAudioProcess`, and `ChromeAudioClient`. `start` uses hidden-window flags, line-buffered text pipes and a bounded ready wait; early EOF, timeout and non-zero exit include bounded stderr diagnostics. `stop` sends `q`, waits 10 seconds, kills on timeout, and requires a non-empty WAV.

- [ ] **Step 8: Run Task 2 tests and commit**

Run: `python -m unittest tests.test_chrome_audio_helper tests.test_chrome_audio -v`

Expected: all pass.

```powershell
git add native/chrome_audio_capture scripts/build-chrome-audio.ps1 src/bizneo_recorder/chrome_audio.py tests/test_chrome_audio_helper.py tests/test_chrome_audio.py
git commit -m "feat: capture Chrome process audio with Windows loopback"
```

---

### Task 3: FFmpeg capture and final audio composition

**Files:**
- Modify: `src/bizneo_recorder/ffmpeg.py`
- Modify: `tests/test_ffmpeg.py`

**Interfaces:**
- Produces: `build_capture_command(config, capture_path) -> list[str]`.
- Produces: `build_finalize_command(config, paths) -> list[str]`.
- Produces: `run_finalize(config, paths) -> None`.

- [ ] **Step 1: Replace the old command test with failing mode-specific tests**

```python
def test_capture_command_records_full_desktop_without_microphone(self) -> None:
    config = RecordingConfig(Path("videos"), 321)
    command = client.build_capture_command(config, Path("capture.mkv"))
    self.assertIn("desktop", command)
    self.assertNotIn("dshow", command)

def test_capture_command_adds_only_selected_microphone(self) -> None:
    config = RecordingConfig(Path("videos"), 321, Microphone("USB Mic"))
    command = client.build_capture_command(config, Path("capture.mkv"))
    self.assertIn("audio=USB Mic", command)

def test_finalize_command_uses_chrome_as_only_audio_without_microphone(self) -> None:
    command = client.build_finalize_command(config_without_mic, paths)
    self.assertIn(str(paths.chrome_audio), command)
    self.assertNotIn("amix", " ".join(command))

def test_finalize_command_mixes_chrome_and_microphone(self) -> None:
    command = client.build_finalize_command(config_with_mic, paths)
    self.assertIn("amix=inputs=2", " ".join(command))
```

- [ ] **Step 2: Run FFmpeg tests and verify RED**

Run: `python -m unittest tests.test_ffmpeg -v`

Expected: methods/signatures absent.

- [ ] **Step 3: Implement capture commands**

The capture command always uses `gdigrab -i desktop`, the selected scale/pad filter, H.264 `veryfast` CRF 18 and MKV output. When `microphone is None`, map only video; otherwise add DirectShow, resample mic audio to 44.1 kHz stereo and encode it as lossless PCM in the temporary MKV.

- [ ] **Step 4: Implement finalization commands**

Use capture MKV as input 0 and Chrome WAV as input 1. Without mic, map `0:v` and `1:a`; with mic, filter `[1:a][0:a]amix=inputs=2:duration=longest:dropout_transition=0,aresample=44100:async=1:first_pts=0[a]`. Copy H.264 video, encode AAC 192 kb/s, apply `+faststart` and `-shortest`, and write `paths.partial`.

`run_finalize` executes synchronously with hidden-window flags and raises `FFmpegError` containing bounded stderr when the return code is non-zero.

- [ ] **Step 5: Run FFmpeg tests and commit**

Run: `python -m unittest tests.test_ffmpeg -v`

Expected: all pass.

```powershell
git add src/bizneo_recorder/ffmpeg.py tests/test_ffmpeg.py
git commit -m "feat: compose Chrome and optional microphone audio"
```

---

### Task 4: Multi-process recorder lifecycle and recovery

**Files:**
- Modify: `src/bizneo_recorder/recorder.py`
- Modify: `tests/test_recorder.py`

**Interfaces:**
- Consumes: `ChromeAudioClient.start`, `FFmpegClient.build_capture_command`, `FFmpegClient.run_finalize`.
- Preserves: `Recorder.start(config) -> Path`, `Recorder.stop() -> Path`, `Recorder.poll() -> int | None`.

- [ ] **Step 1: Write failing lifecycle tests**

Cover these independent behaviors:

```python
def test_start_prepares_chrome_audio_before_screen_capture(self) -> None:
    recorder.start(config)
    self.assertEqual(events[:2], ["chrome-ready", "screen-started"])

def test_start_failure_stops_helper_and_does_not_enter_recording(self) -> None:
    with self.assertRaisesRegex(RecorderError, "pantalla"):
        recorder.start(config)
    self.assertTrue(chrome_handle.stopped)
    self.assertEqual(recorder.state, RecorderState.IDLE)

def test_stop_finalizes_and_removes_intermediates_only_after_success(self) -> None:
    result = recorder.stop()
    self.assertEqual(result, recorder.final_path)
    self.assertFalse(paths.capture.exists())
    self.assertFalse(paths.chrome_audio.exists())

def test_finalize_failure_preserves_capture_and_chrome_wav(self) -> None:
    with self.assertRaises(RecorderError):
        recorder.stop()
    self.assertTrue(paths.capture.exists())
    self.assertTrue(paths.chrome_audio.exists())
```

- [ ] **Step 2: Run recorder tests and verify RED**

Run: `python -m unittest tests.test_recorder -v`

Expected: constructor/client and lifecycle expectations fail.

- [ ] **Step 3: Implement coordinated start**

Inject `ChromeAudioClient` and separate process factories where needed. `start` allocates `RecordingPaths`, starts Chrome audio, then screen capture. Any failure performs bounded cleanup, resets state and retains diagnostics. Only set `RECORDING` after both processes are alive.

- [ ] **Step 4: Implement coordinated stop and finalization**

Stop screen capture with `q`, stop Chrome helper, validate intermediate files, call `run_finalize`, promote partial to final, then remove capture/WAV. On any failure, keep intermediates, set `IDLE`, clear live process handles, and raise one `RecorderError` with the latest actionable diagnostics.

- [ ] **Step 5: Run recorder and regression tests**

Run: `python -m unittest discover -s tests -t . -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src/bizneo_recorder/recorder.py tests/test_recorder.py
git commit -m "feat: coordinate conference capture lifecycle"
```

---

### Task 5: Minimal conference UI and diagnostics

**Files:**
- Modify: `src/bizneo_recorder/app.py`
- Modify: `src/bizneo_recorder/main.py`
- Modify: `tests/test_main.py`
- Create: `tests/test_app.py`

**Interfaces:**
- `build_recording_config(output_dir, chrome_process_id, include_microphone, microphone, resolution_label, fps_label)`.
- UI dependency: injectable `chrome_finder: Callable[[], int | None]` for deterministic tests.

- [ ] **Step 1: Write failing config and UI-state tests**

```python
def test_build_config_defaults_to_chrome_only(self) -> None:
    config = build_recording_config(Path("videos"), 321, False, Microphone("Mic"), "Full HD 1080p", "30 FPS")
    self.assertIsNone(config.microphone)

def test_build_config_uses_microphone_only_when_enabled(self) -> None:
    config = build_recording_config(Path("videos"), 321, True, Microphone("Mic"), "Full HD 1080p", "30 FPS")
    self.assertEqual(config.microphone, Microphone("Mic"))
```

UI tests instantiate Tk under the existing Windows session and assert: title `Conference Recorder`, initial microphone flag false, mic selector hidden, start disabled without Chrome, start enabled with Chrome, and the selector shown only after the checkbox is activated.

- [ ] **Step 2: Run UI/main tests and verify RED**

Run: `python -m unittest tests.test_main tests.test_app -v`

Expected: config signature and conference controls absent.

- [ ] **Step 3: Implement the minimal interface**

Keep the existing palette and accessibility. Replace the header/subtitle, add a Chrome status row and refresh action, add a checkbox `Incloure el meu micròfon`, and pack/unpack the microphone selector panel based on the checkbox. Keep quality controls in a visually secondary compact section. Use `Vídeos\Conference Recorder`, `Gravar conferència`, `Finalitzar i guardar`, a visible timer and output-folder action.

Refresh Chrome on startup and immediately before start. Enumerate microphones only after the option is enabled. Disable all mutable controls during recording and restore states consistently after success/failure.

- [ ] **Step 4: Extend self-test**

`run_self_test` reports FFmpeg/H.264, helper/process-loopback compatibility, Chrome detection and microphones as optional information. Exit success requires H.264 and helper support; it does not require Chrome to be running or a microphone to exist.

- [ ] **Step 5: Run tests, import checks and visual smoke**

Run:

```powershell
python -m unittest discover -s tests -t . -v
python -m compileall -q src scripts tests
ruff check src tests scripts
```

Open the development GUI, inspect Chrome missing/detected states, toggle mic, keyboard focus, quality selectors, record/stop states and fixed-size layout; close it without starting a real recording.

- [ ] **Step 6: Commit**

```powershell
git add src/bizneo_recorder/app.py src/bizneo_recorder/main.py tests/test_main.py tests/test_app.py
git commit -m "feat: add minimal conference recording interface"
```

---

### Task 6: Portable build, real recording verification, and documentation

**Files:**
- Modify: `scripts/build-portable.ps1`
- Modify: `scripts/smoke-recording.py`
- Modify: `scripts/verify-recording.ps1`
- Modify: `README.md`
- Modify: `pyproject.toml`
- Modify: `docs/usage.md`
- Modify: `docs/architecture.md`
- Modify: `docs/portable-readme.txt`
- Modify: `docs/verification.md`

**Interfaces:**
- Portable layout: `Conference Recorder.exe`, `tools/ffmpeg.exe`, `tools/chrome-audio-capture.exe`, notices/licenses and `LLEGEIX-ME.txt`.
- Output archive: `outputs/Conference-Recorder-Portable.zip`.

- [ ] **Step 1: Add failing portable-layout assertions**

Update `Assert-PortableLayout` before copying the helper or renamed executable so `scripts/build-portable.ps1 -ValidateOnly` fails specifically for missing `Conference Recorder.exe` and `tools\chrome-audio-capture.exe`.

- [ ] **Step 2: Run validation and verify RED**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1 -ValidateOnly`

Expected: failure naming a missing conference/helper artifact.

- [ ] **Step 3: Update build and smoke scripts**

Compile the helper into `work/portable-build/native`, rename the PyInstaller executable and portable directory/archive, copy both tools, and validate both `--self-test` commands. Update smoke recording to require a detected Chrome root, accept `--include-microphone`, and use the new clients. Extend the PowerShell verifier to require exactly one H.264 video stream and one AAC audio stream with the selected dimensions/FPS.

- [ ] **Step 4: Update all user and architecture documentation**

Document full-screen capture, Chrome-only audio, the optional microphone default, minimum Windows build, privacy, failure recovery, folder paths, build steps and the exact module/tool relationships. Keep `docs/architecture.md` tree synchronized with `native/`, `processes.py` and `chrome_audio.py`.

- [ ] **Step 5: Run automated verification**

```powershell
python -m unittest discover -s tests -t . -v
ruff check src tests scripts
python -m compileall -q src scripts tests
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
& '.\outputs\Conference Recorder\Conference Recorder.exe' --self-test
```

Expected: clean tests/lint/compile, successful portable build and diagnostic exit 0.

- [ ] **Step 6: Run real audio-isolation recordings**

With Chrome playing a known spoken sample:

1. Record 5–10 seconds at 1080p/30 without mic.
2. Simultaneously play a distinct sound in another application and confirm it is absent from the result.
3. Repeat at 720p/60 with mic enabled and confirm Chrome plus mic are audible.
4. Probe both MP4 files with `scripts/verify-recording.ps1`.
5. Remove the privacy-sensitive sample files after recording the measured results in `docs/verification.md`.

- [ ] **Step 7: Inspect the packaged UI and ZIP**

Open the packaged executable, visually inspect the states and controls, stop it, extract the ZIP to `work/zip-test`, rerun `--self-test`, and calculate the final ZIP SHA-256 for `docs/verification.md`.

- [ ] **Step 8: Final regression review and commit**

Run `git diff --check`, inspect `git status --short`, confirm no generated file outside `outputs/`/`work/`, and verify `docs/architecture.md` matches the tree.

```powershell
git add README.md pyproject.toml scripts docs src tests native
git commit -m "docs: deliver portable Conference Recorder"
```
