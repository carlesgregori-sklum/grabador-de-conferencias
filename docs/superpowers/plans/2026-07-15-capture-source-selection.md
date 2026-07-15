# Capture Source Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Afegir selecció de pantalla principal, monitor concret o pestanya real de Chrome, amb micròfon opcional i eixida MP4.

**Architecture:** El mode actual conserva FFmpeg `gdigrab` i WASAPI per procés. Els modes seleccionables obrin una pàgina temporal en Chrome, servida només en loopback, que usa `getDisplayMedia()` i envia fragments WebM ordenats al procés Python. `Recorder` coordina el pont, FFmpeg, l’àudio de Chrome i el micròfon segons el mode.

**Tech Stack:** Python 3.13, Tkinter, `ThreadingHTTPServer`, HTML/JavaScript MediaRecorder, Chrome getDisplayMedia, FFmpeg, WASAPI Process Loopback, unittest, PowerShell i PyInstaller.

## Global Constraints

- Windows 10 build 20348 o posterior.
- Cap extensió de Chrome ni dependència Python nova.
- El servidor ha d’escoltar exclusivament en `127.0.0.1` i usar un token de 256 bits per sessió.
- La pantalla principal continua sent el mode inicial.
- La pestanya de Chrome usa només el seu àudio; pantalla principal i monitor usen l’àudio de l’arbre de Chrome.
- El micròfon és opcional i està desactivat per defecte en tots els modes.
- Els resultats continuen en `Vídeos\Conference Recorder` com MP4 H.264/AAC.
- Els temporals només s’eliminen després d’una finalització correcta.
- Cada tasca segueix el cicle TDD roig-verd i acaba amb un commit local.

---

## Estructura de fitxers

- `src/bizneo_recorder/models.py`: modes, configuració i rutes de sessió.
- `src/bizneo_recorder/processes.py`: PID arrel i ruta executable de Chrome.
- `src/bizneo_recorder/browser_capture.py`: servidor loopback, protocol i estat del navegador.
- `src/bizneo_recorder/assets/browser_capture.html`: UI local i MediaRecorder.
- `src/bizneo_recorder/ffmpeg.py`: captura de micròfon i finalització dels tres modes.
- `src/bizneo_recorder/recorder.py`: coordinació dels processos segons el mode.
- `src/bizneo_recorder/app.py`: selector de font i feedback de selecció.
- `src/bizneo_recorder/main.py`: construcció del pont i localització de recursos.
- `tests/test_models.py`, `tests/test_processes.py`, `tests/test_browser_capture.py`, `tests/test_ffmpeg.py`, `tests/test_recorder.py`, `tests/test_app.py`, `tests/test_main.py`: cobertura unitària i d’integració local.
- `pyproject.toml`, `scripts/build-portable.ps1`: inclusió de l’asset HTML.
- `README.md`, `docs/usage.md`, `docs/architecture.md`, `docs/portable-readme.txt`, `docs/verification.md`: documentació sincronitzada.

### Task 1: Model de fonts i rutes temporals

**Files:**
- Modify: `src/bizneo_recorder/models.py`
- Modify: `src/bizneo_recorder/app.py`
- Test: `tests/test_models.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Produces: `CaptureMode`, `parse_capture_mode(label)`, `RecordingConfig.capture_mode`, `RecordingPaths.browser_capture`, `RecordingPaths.microphone_audio`.
- Consumes: presets de resolució i FPS existents.

- [ ] **Step 1: Write failing model tests**

```python
def test_capture_labels_map_to_three_modes(self):
    self.assertEqual(parse_capture_mode("Tota la pantalla principal"), CaptureMode.PRIMARY_SCREEN)
    self.assertEqual(parse_capture_mode("Una pantalla concreta"), CaptureMode.SELECTED_MONITOR)
    self.assertEqual(parse_capture_mode("Una pestanya de Chrome"), CaptureMode.CHROME_TAB)

def test_paths_cover_browser_and_microphone_temporaries(self):
    paths = RecordingConfig(Path("videos"), 321).next_paths()
    self.assertTrue(str(paths.browser_capture).endswith(".browser.webm"))
    self.assertTrue(str(paths.microphone_audio).endswith(".microphone.wav"))
```

- [ ] **Step 2: Run tests and verify red**

Run: `$env:PYTHONPATH=(Resolve-Path src).Path; python -m unittest tests.test_models -v`

Expected: imports for `CaptureMode` and the new paths fail.

- [ ] **Step 3: Implement the model**

```python
class CaptureMode(str, Enum):
    PRIMARY_SCREEN = "primary_screen"
    SELECTED_MONITOR = "selected_monitor"
    CHROME_TAB = "chrome_tab"

CAPTURE_MODE_LABELS = {
    "Tota la pantalla principal": CaptureMode.PRIMARY_SCREEN,
    "Una pantalla concreta": CaptureMode.SELECTED_MONITOR,
    "Una pestanya de Chrome": CaptureMode.CHROME_TAB,
}

def parse_capture_mode(label: str) -> CaptureMode:
    try:
        return CAPTURE_MODE_LABELS[label]
    except KeyError as error:
        raise ValueError(f"font de captura no admesa: {label!r}") from error
```

Add `capture_mode: CaptureMode = CaptureMode.PRIMARY_SCREEN` to `RecordingConfig`. Add `browser_capture` and `microphone_audio` to `RecordingPaths`, include them in `intermediates()`, and allocate `.browser.webm` and `.microphone.wav` names in `next_paths()`.

- [ ] **Step 4: Extend `build_recording_config`**

Add `capture_mode_label: str` and pass `parse_capture_mode(capture_mode_label)` into `RecordingConfig`. Update every caller and test fixture with the default label `Tota la pantalla principal`.

- [ ] **Step 5: Run tests and commit**

Run: `$env:PYTHONPATH=(Resolve-Path src).Path; python -m unittest tests.test_models tests.test_main -v`

Expected: all tests pass.

```powershell
git add src/bizneo_recorder/models.py src/bizneo_recorder/app.py tests/test_models.py tests/test_main.py
git commit -m "feat: model selectable capture sources"
```

### Task 2: Ruta executable de Chrome

**Files:**
- Modify: `src/bizneo_recorder/processes.py`
- Test: `tests/test_processes.py`

**Interfaces:**
- Consumes: PID retornat per `find_chrome_root()`.
- Produces: `query_process_executable(pid: int) -> Path` i `find_chrome() -> ChromeProcess | None`.

- [ ] **Step 1: Write failing tests for the pure selection object**

```python
def test_chrome_process_contains_root_and_executable(self):
    chrome = ChromeProcess(321, Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
    self.assertEqual(chrome.pid, 321)
    self.assertEqual(chrome.executable.name, "chrome.exe")
```

Patch `enumerate_processes` and `query_process_executable` in a second test and require `find_chrome()` to return the selected PID plus the queried path.

- [ ] **Step 2: Run test and verify red**

Run: `$env:PYTHONPATH=(Resolve-Path src).Path; python -m unittest tests.test_processes -v`

Expected: `ChromeProcess` and `find_chrome` are absent.

- [ ] **Step 3: Implement Win32 path lookup**

```python
@dataclass(frozen=True, slots=True)
class ChromeProcess:
    pid: int
    executable: Path

def query_process_executable(pid: int) -> Path:
    # OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION),
    # QueryFullProcessImageNameW into a 32768-char buffer,
    # CloseHandle in finally, and raise ProcessDiscoveryError on failure.
```

`find_chrome()` enumerates once, selects the root PID and returns `ChromeProcess`. Retain `find_chrome_root()` as a compatibility wrapper returning only `.pid`.

- [ ] **Step 4: Run tests and commit**

Run: `$env:PYTHONPATH=(Resolve-Path src).Path; python -m unittest tests.test_processes tests.test_main -v`

```powershell
git add src/bizneo_recorder/processes.py tests/test_processes.py
git commit -m "feat: locate the running Chrome executable"
```

### Task 3: Pont local i pàgina de captura

**Files:**
- Create: `src/bizneo_recorder/browser_capture.py`
- Create: `src/bizneo_recorder/assets/browser_capture.html`
- Create: `tests/test_browser_capture.py`

**Interfaces:**
- Consumes: `CaptureMode`, output `.browser.webm`, executable de Chrome.
- Produces: `BrowserCaptureMetadata(display_surface: str, has_audio: bool, mime_type: str)` and `BrowserCaptureBridge(page_html: str, mode: CaptureMode, output_path: Path, fps: int, process_factory=subprocess.Popen, token_factory=secrets.token_urlsafe)`.
- Produces: `start(chrome_executable: Path) -> None`, `wait_ready(timeout: float = 120.0) -> BrowserCaptureMetadata`, `begin(timeout: float = 10.0) -> None`, `stop(timeout: float = 15.0) -> None`, `poll() -> str | None`, and `close() -> None`.

- [ ] **Step 1: Write failing protocol tests**

Start the bridge with a temporary WebM path and inject a deterministic token. Use `urllib.request` to assert:

```python
def test_rejects_wrong_token(self):
    with self.assertRaises(HTTPError) as error:
        urlopen(f"{bridge.base_url}/api/wrong/command")
    self.assertEqual(error.exception.code, 404)

def test_chunks_are_ordered_and_duplicate_retry_is_idempotent(self):
    post("/chunk/0", b"webm-a")
    post("/chunk/0", b"webm-a")
    post("/chunk/1", b"webm-b")
    self.assertEqual(path.read_bytes(), b"webm-awebm-b")
```

Also test loopback host, ready metadata validation, oversized chunk rejection, command state, completion, timeout and clean shutdown.

- [ ] **Step 2: Run tests and verify red**

Run: `$env:PYTHONPATH=(Resolve-Path src).Path; python -m unittest tests.test_browser_capture -v`

Expected: module import fails.

- [ ] **Step 3: Implement bridge state and handler**

Use `ThreadingHTTPServer(("127.0.0.1", 0), Handler)`, a `Condition`, bounded JSON bodies and `secrets.token_urlsafe(32)`. `ready` accepts only `monitor` for `SELECTED_MONITOR`, or `browser` plus `has_audio=true` for `CHROME_TAB`. Chunks are capped at 16 MiB and appended only in expected sequence.

`start()` binds the server and calls the injected process factory with `[str(chrome_executable), capture_url]`, `stdout/stderr=DEVNULL`, and `CREATE_NO_WINDOW`.

- [ ] **Step 4: Implement the HTML controller**

The page reads `mode` and token from its served configuration, requires a button click, and calls:

```javascript
const stream = await navigator.mediaDevices.getDisplayMedia({
  video: {
    frameRate: { ideal: requestedFps },
    displaySurface: mode === "tab" ? "browser" : "monitor",
  },
  audio: mode === "tab" ? {
    suppressLocalAudioPlayback: false,
  } : false,
  selfBrowserSurface: "exclude",
  surfaceSwitching: "exclude",
  systemAudio: "exclude",
});
```

Validate `track.getSettings().displaySurface`, require an audio track in tab mode, POST `/ready`, poll `/command`, and use `MediaRecorder(stream, {mimeType: "video/webm;codecs=vp9,opus"})` with a VP8 fallback. Queue one-second chunks sequentially and POST `/complete` only after the final chunk is acknowledged. `track.onended` stops safely.

- [ ] **Step 5: Run bridge tests and commit**

Run: `$env:PYTHONPATH=(Resolve-Path src).Path; python -m unittest tests.test_browser_capture -v`

```powershell
git add src/bizneo_recorder/browser_capture.py src/bizneo_recorder/assets/browser_capture.html tests/test_browser_capture.py
git commit -m "feat: capture browser-selected media over loopback"
```

### Task 4: FFmpeg per als modes del navegador

**Files:**
- Modify: `src/bizneo_recorder/ffmpeg.py`
- Test: `tests/test_ffmpeg.py`

**Interfaces:**
- Consumes: `CaptureMode`, `RecordingConfig`, new paths.
- Produces: `build_microphone_command`, mode-aware `build_finalize_command`.

- [ ] **Step 1: Write failing command tests**

```python
def test_microphone_command_writes_stereo_pcm(self):
    command = client.build_microphone_command(config, paths.microphone_audio)
    self.assertIn("audio=USB Mic", command)
    self.assertIn("pcm_s16le", command)

def test_tab_finalize_uses_webm_audio_and_optional_microphone(self):
    command = client.build_finalize_command(tab_config, paths)
    self.assertEqual(command.count(str(paths.browser_capture)), 1)
    self.assertNotIn(str(paths.chrome_audio), command)
    self.assertIn("amix=inputs=2", " ".join(command))
```

Add monitor assertions for browser video + Chrome WAV and primary assertions that retain `-c:v copy`.

- [ ] **Step 2: Run tests and verify red**

Run: `$env:PYTHONPATH=(Resolve-Path src).Path; python -m unittest tests.test_ffmpeg -v`

- [ ] **Step 3: Implement microphone and mode-aware finalization**

`build_microphone_command` captures only DirectShow audio as PCM 44.1 kHz stereo WAV. For browser modes, use the WebM as input zero, scale/pad to the selected output size, set `libx264`, `veryfast`, CRF 18, yuv420p and the selected FPS.

Audio mappings:

- monitor/no mic: Chrome WAV.
- monitor/mic: Chrome WAV + microphone WAV through `amix`.
- tab/no mic: audio from WebM.
- tab/mic: WebM audio + microphone WAV through `amix`.

- [ ] **Step 4: Run tests and commit**

Run: `$env:PYTHONPATH=(Resolve-Path src).Path; python -m unittest tests.test_ffmpeg -v`

```powershell
git add src/bizneo_recorder/ffmpeg.py tests/test_ffmpeg.py
git commit -m "feat: finalize monitor and tab captures"
```

### Task 5: Coordinació del Recorder

**Files:**
- Modify: `src/bizneo_recorder/recorder.py`
- Test: `tests/test_recorder.py`

**Interfaces:**
- Consumes: `BrowserCaptureBridge`, Chrome audio client, FFmpeg commands.
- Produces: `BrowserBridgeFactory = Callable[[RecordingConfig, RecordingPaths], BrowserCaptureBridge]`, `Recorder(..., browser_bridge_factory: BrowserBridgeFactory | None = None)`, `Recorder.start(config: RecordingConfig, chrome_executable: Path | None = None) -> Path`, mode-aware `poll() -> int | None` and `stop(timeout: float = 15.0) -> Path`.

- [ ] **Step 1: Write failing lifecycle tests**

Cover these event sequences:

```python
self.assertEqual(events, [
    "browser-opened", "browser-ready", "chrome-ready",
    "browser-begun", "browser-stopped", "chrome-stopped", "finalized",
])
```

For tab mode require no `chrome-ready`; for tab+mic require `microphone-started`; for picker cancellation require reset to `IDLE`; for bridge failure require all live native processes stopped and temporaries retained.

- [ ] **Step 2: Run tests and verify red**

Run: `$env:PYTHONPATH=(Resolve-Path src).Path; python -m unittest tests.test_recorder -v`

- [ ] **Step 3: Implement mode dispatch**

Keep `_start_primary_screen()` as the current path. Add `_start_browser_capture()` that creates the bridge, opens Chrome, waits for ready, starts Chrome audio only for monitor mode, starts optional mic, sends `begin`, waits for `started`, and then enters `RECORDING`.

Generalize process stderr draining and ordered stop. `poll()` checks the active FFmpeg processes, Chrome helper and browser bridge. `stop()` stops the browser first, then mic/Chrome, runs finalization, promotes the MP4, removes only applicable intermediates and closes the bridge in `finally`.

- [ ] **Step 4: Run tests and commit**

Run: `$env:PYTHONPATH=(Resolve-Path src).Path; python -m unittest tests.test_recorder -v`

```powershell
git add src/bizneo_recorder/recorder.py tests/test_recorder.py
git commit -m "feat: coordinate selected capture sources"
```

### Task 6: UI i integració de l’aplicació

**Files:**
- Modify: `src/bizneo_recorder/app.py`
- Modify: `src/bizneo_recorder/main.py`
- Test: `tests/test_app.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: three capture labels, `find_chrome()`, recorder mode dispatch.
- Produces: accessible source selector and dynamic primary action.

- [ ] **Step 1: Write failing UI tests**

Assert the initial label, three radio options, dynamic button labels, mic hidden by default and `build_recording_config` mode mapping. Patch the recorder to assert `chrome_executable` is passed only for browser modes.

- [ ] **Step 2: Run tests and verify red**

Run: `$env:PYTHONPATH=(Resolve-Path src).Path; python -m unittest tests.test_app tests.test_main -v`

- [ ] **Step 3: Implement the compact source selector**

Use one `LabelFrame` with three `ttk.Radiobutton` rows and short secondary text. Default to `Tota la pantalla principal`. Update the subtitle and status text per mode. Disable all source controls during waiting, recording and finalization.

Replace the PID-only refresh with a `ChromeProcess` value so the start worker has both PID and executable. Load the controller with `importlib.resources.files("bizneo_recorder").joinpath("assets/browser_capture.html").read_text(encoding="utf-8")` and inject that HTML string into the bridge factory. This works from source and from the `_runtime/bizneo_recorder/assets` package data collected by PyInstaller.

- [ ] **Step 4: Run tests, visually inspect and commit**

Run: `$env:PYTHONPATH=(Resolve-Path src).Path; python -m unittest tests.test_app tests.test_main -v`

Open the development app, check all three selector states, dynamic button text, keyboard focus, mic panel, no clipping and clean close without starting a capture.

```powershell
git add src/bizneo_recorder/app.py src/bizneo_recorder/main.py tests/test_app.py tests/test_main.py
git commit -m "feat: add capture source selector UI"
```

### Task 7: Paquet, documentació i verificació real

**Files:**
- Modify: `pyproject.toml`
- Modify: `scripts/build-portable.ps1`
- Modify: `scripts/smoke-recording.py`
- Modify: `README.md`
- Modify: `docs/usage.md`
- Modify: `docs/architecture.md`
- Modify: `docs/portable-readme.txt`
- Modify: `docs/verification.md`
- Modify: `tests/test_build_scripts.py`

**Interfaces:**
- Consumes: completed application and browser capture asset.
- Produces: rebuilt portable ZIP and synchronized documentation.

- [ ] **Step 1: Write failing package tests**

Require package data for `assets/*.html`, PyInstaller `--add-data`, and `Assert-PortableLayout` validation of `_runtime/bizneo_recorder/assets/browser_capture.html`.

- [ ] **Step 2: Run package tests and verify red**

Run: `$env:PYTHONPATH=(Resolve-Path src).Path; python -m unittest tests.test_build_scripts -v`

- [ ] **Step 3: Add asset packaging and documentation**

Add `[tool.setuptools.package-data] bizneo_recorder = ["assets/*.html"]`. Pass `--add-data "$projectRoot\src\bizneo_recorder\assets;bizneo_recorder\assets"` to PyInstaller, validate `_runtime\bizneo_recorder\assets\browser_capture.html`, and document the three flows, exact tab audio, picker cancellation, local-only bridge, temporary recovery files and current limitations.

- [ ] **Step 4: Run the complete automated gate**

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
python -m unittest discover -s tests -p "test_*.py" -v
python -m ruff check src tests scripts
python -m compileall -q src tests scripts
git diff --check
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1 -ValidateOnly
```

Expected: zero failures and a new `outputs/Conference-Recorder-Portable.zip`.

- [ ] **Step 5: Verify real captures**

Record short samples for primary screen 1080p/30, selected monitor 720p/60 and one Chrome tab with shared audio. Repeat one browser-selected mode with mic enabled. Use `ffprobe` to require exactly one H.264 stream, one AAC stream, selected size/FPS and positive duration. Exercise cancel, wrong source and stop-sharing paths. Keep samples only under ignored `work/`.

- [ ] **Step 6: Visual QA and final commit**

Launch the packaged app, inspect initial state and all source selections, start no recording unless the relevant browser selector can be completed safely, and close every temporary page/window. Record exact commands, durations, package bytes and SHA-256 in `docs/verification.md`.

```powershell
git add pyproject.toml scripts README.md docs tests/test_build_scripts.py
git commit -m "docs: deliver selectable capture sources"
```
