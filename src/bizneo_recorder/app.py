from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .ffmpeg import FFmpegClient, FFmpegError
from .models import (
    CAPTURE_MODE_LABELS,
    RESOLUTION_PRESETS,
    SUPPORTED_FPS,
    CaptureMode,
    Microphone,
    RecordingConfig,
    get_resolution_preset,
    parse_capture_mode,
    parse_fps,
)
from .processes import ChromeProcess, ProcessDiscoveryError, find_chrome
from .recorder import Recorder, RecorderError, RecorderState
from .ui import (
    AMBER,
    BACKGROUND,
    BORDER,
    CORAL,
    ERROR,
    GREEN,
    MUTED,
    SUBTLE,
    SURFACE,
    SURFACE_HOVER,
    SURFACE_RAISED,
    TEXT,
    VIOLET,
    AnimatedActionButton,
    CaptureCard,
    OrbitalRecorder,
    ToggleSwitch,
    WaveformIndicator,
)


CAPTURE_HELP: dict[CaptureMode, str] = {
    CaptureMode.PRIMARY_SCREEN: (
        "Captura la pantalla principal y el audio que suena en Chrome."
    ),
    CaptureMode.SELECTED_MONITOR: (
        "Chrome abrirá el selector para que elijas una pantalla completa."
    ),
    CaptureMode.CHROME_TAB: (
        "Elige una pestaña y activa «Compartir también el audio» en Chrome."
    ),
}
CAPTURE_ACTION: dict[CaptureMode, str] = {
    CaptureMode.PRIMARY_SCREEN: "Iniciar grabación",
    CaptureMode.SELECTED_MONITOR: "Elegir pantalla y grabar",
    CaptureMode.CHROME_TAB: "Elegir pestaña y grabar",
}
CAPTURE_DETAILS: dict[CaptureMode, tuple[str, str]] = {
    CaptureMode.PRIMARY_SCREEN: ("Sin selector", "monitor"),
    CaptureMode.SELECTED_MONITOR: ("Elige un monitor", "screen"),
    CaptureMode.CHROME_TAB: ("Audio de la pestaña", "tab"),
}


def format_elapsed(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    minutes, seconds_part = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds_part:02d}"


def build_recording_config(
    output_dir: Path,
    chrome_process_id: int,
    include_microphone: bool,
    microphone: Microphone | None,
    resolution_label: str,
    fps_label: str,
    capture_mode_label: str = "Pantalla completa",
) -> RecordingConfig:
    if include_microphone and microphone is None:
        raise ValueError("activa y selecciona un micrófono o desactiva la opción")
    preset = get_resolution_preset(resolution_label)
    return RecordingConfig(
        output_dir,
        chrome_process_id,
        microphone=microphone if include_microphone else None,
        width=preset.width,
        height=preset.height,
        fps=parse_fps(fps_label),
        capture_mode=parse_capture_mode(capture_mode_label),
    )


class BizneoRecorderApp:
    """Dark, animated UI for screen, Chrome audio and optional microphone."""

    def __init__(
        self,
        root: tk.Tk,
        client: FFmpegClient,
        recorder: Recorder,
        chrome_finder: Callable[[], ChromeProcess | None] = find_chrome,
        directory_chooser: Callable[..., str] = filedialog.askdirectory,
    ) -> None:
        self.root = root
        self.client = client
        self.recorder = recorder
        self.chrome_finder = chrome_finder
        self.directory_chooser = directory_chooser
        self.output_dir = Path.home() / "Videos" / "Grabador de conferencias"
        self.chrome_process: ChromeProcess | None = None
        self.microphones: list[Microphone] = []
        self.started_at = 0.0
        self.current_video: Path | None = None
        self.close_after_stop = False
        self.loading_microphones = False

        self.status_var = tk.StringVar(value="Comprobando Chrome…")
        self.hero_status_var = tk.StringVar(value="COMPROBANDO CHROME")
        self.chrome_state_var = tk.StringVar(value="Comprobando Chrome")
        self.elapsed_var = tk.StringVar(value="00:00")
        self.include_microphone_var = tk.BooleanVar(value=False)
        self.microphone_var = tk.StringVar()
        self.microphone_state_var = tk.StringVar(value="El micrófono está desactivado")
        self.resolution_var = tk.StringVar(value="Full HD 1080p")
        self.fps_var = tk.StringVar(value="30 FPS")
        self.capture_mode_var = tk.StringVar(value="Pantalla completa")
        self.capture_help_var = tk.StringVar(
            value=CAPTURE_HELP[CaptureMode.PRIMARY_SCREEN]
        )
        self.output_path_var = tk.StringVar(value=self._output_path_label())

        self._configure_window()
        self._build_interface()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Escape>", lambda _event: self._on_close())
        self.root.bind("<Control-o>", lambda _event: self.open_output_folder())
        self.refresh_chrome()

    def _configure_window(self) -> None:
        self.root.title("Grabador de conferencias")
        width = 920
        height = 900
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        left = max(0, (screen_width - width) // 2)
        top = max(0, (screen_height - height) // 2 - 8)
        self.root.geometry(f"{width}x{height}+{left}+{top}")
        self.root.minsize(900, 860)
        self.root.maxsize(1040, 980)
        self.root.configure(bg=BACKGROUND)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Dark.TCombobox",
            fieldbackground=SURFACE_RAISED,
            background=SURFACE_RAISED,
            foreground=TEXT,
            arrowcolor=MUTED,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=8,
            font=("Segoe UI", 10),
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", SURFACE_RAISED), ("disabled", SURFACE)],
            foreground=[("disabled", SUBTLE), ("readonly", TEXT)],
            bordercolor=[("focus", VIOLET)],
        )
        self.root.option_add("*TCombobox*Listbox*Background", SURFACE_RAISED)
        self.root.option_add("*TCombobox*Listbox*Foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox*selectBackground", VIOLET)
        self.root.option_add("*TCombobox*Listbox*selectForeground", TEXT)

    def _build_interface(self) -> None:
        container = tk.Frame(self.root, bg=BACKGROUND, padx=38, pady=22)
        container.pack(fill="both", expand=True)

        header = tk.Frame(container, bg=BACKGROUND)
        header.pack(fill="x")
        brand = tk.Frame(header, bg=BACKGROUND)
        brand.pack(side="left")
        mark = tk.Canvas(
            brand,
            width=34,
            height=34,
            bg=BACKGROUND,
            highlightthickness=0,
            bd=0,
        )
        mark.pack(side="left", padx=(0, 10))
        mark.create_oval(3, 3, 31, 31, outline=CORAL, width=2)
        mark.create_oval(10, 10, 24, 24, fill=CORAL, outline="")
        tk.Label(
            brand,
            text="Grabador de conferencias",
            bg=BACKGROUND,
            fg=TEXT,
            font=("Segoe UI Semibold", 15),
        ).pack(side="left")

        chrome_controls = tk.Frame(header, bg=BACKGROUND)
        chrome_controls.pack(side="right")
        chrome_pill = tk.Frame(
            chrome_controls,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=12,
            pady=7,
        )
        chrome_pill.pack(side="left")
        self.chrome_indicator = tk.Canvas(
            chrome_pill,
            width=12,
            height=12,
            bg=SURFACE,
            highlightthickness=0,
            bd=0,
        )
        self.chrome_indicator.pack(side="left", padx=(0, 7))
        self.chrome_indicator.create_oval(2, 2, 10, 10, fill=MUTED, outline="", tags="dot")
        self.chrome_state_label = tk.Label(
            chrome_pill,
            textvariable=self.chrome_state_var,
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI Semibold", 9),
        )
        self.chrome_state_label.pack(side="left")
        self.refresh_chrome_button = self._small_button(
            chrome_controls,
            "Comprobar",
            self.refresh_chrome,
        )
        self.refresh_chrome_button.pack(side="left", padx=(9, 0))

        tk.Label(
            container,
            textvariable=self.hero_status_var,
            bg=BACKGROUND,
            fg=TEXT,
            font=("Segoe UI Semibold", 27),
        ).pack(pady=(18, 1))
        tk.Label(
            container,
            text="Graba tu pantalla o una pestaña con total claridad.",
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 11),
        ).pack()

        self.orbital_recorder = OrbitalRecorder(container, width=780, height=176)
        self.orbital_recorder.pack(pady=(0, 2))

        tk.Label(
            container,
            text="¿Qué quieres grabar?",
            bg=BACKGROUND,
            fg=TEXT,
            font=("Segoe UI Semibold", 14),
        ).pack(pady=(0, 7))
        cards_row = tk.Frame(container, bg=BACKGROUND)
        cards_row.pack(fill="x")
        self.capture_mode_cards: dict[str, CaptureCard] = {}
        self.capture_mode_buttons: list[CaptureCard] = []
        for index, (label, mode) in enumerate(CAPTURE_MODE_LABELS.items()):
            detail, icon = CAPTURE_DETAILS[mode]
            card = CaptureCard(
                cards_row,
                label=label,
                detail=detail,
                icon=icon,
                width=258,
                height=116,
                command=lambda selected=label: self._select_capture_label(selected),
            )
            card.pack(side="left", expand=True, padx=(0 if index == 0 else 7, 0))
            card.set_selected(label == self.capture_mode_var.get())
            self.capture_mode_cards[label] = card
            self.capture_mode_buttons.append(card)

        tk.Label(
            container,
            textvariable=self.capture_help_var,
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 9),
            justify="center",
            wraplength=810,
        ).pack(fill="x", pady=(5, 10))

        settings = tk.Frame(
            container,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=18,
            pady=13,
        )
        settings.pack(fill="x")
        self.audio_row = tk.Frame(settings, bg=SURFACE)
        self.audio_row.pack(fill="x")
        tk.Label(
            self.audio_row,
            text="Sonido",
            bg=SURFACE,
            fg=TEXT,
            font=("Segoe UI Semibold", 11),
        ).pack(side="left")
        self.waveform_indicator = WaveformIndicator(
            self.audio_row,
            width=250,
            height=30,
        )
        self.waveform_indicator.pack(side="left", padx=(22, 18), expand=True)
        self.microphone_toggle = ToggleSwitch(
            self.audio_row,
            variable=self.include_microphone_var,
            command=self._microphone_option_changed,
        )
        self.microphone_toggle.pack(side="right")
        microphone_label = tk.Button(
            self.audio_row,
            text="Incluir micrófono",
            command=self.microphone_toggle.invoke,
            bg=SURFACE,
            fg=TEXT,
            activebackground=SURFACE,
            activeforeground=TEXT,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI Semibold", 9),
        )
        microphone_label.pack(side="right", padx=(0, 9))

        self.microphone_panel = tk.Frame(settings, bg=SURFACE)
        selector_row = tk.Frame(self.microphone_panel, bg=SURFACE)
        selector_row.pack(fill="x")
        self.microphone_box = ttk.Combobox(
            selector_row,
            textvariable=self.microphone_var,
            state="readonly",
            style="Dark.TCombobox",
            font=("Segoe UI", 10),
        )
        self.microphone_box.pack(side="left", fill="x", expand=True)
        self.microphone_box.bind("<<ComboboxSelected>>", self._microphone_selected)
        self.refresh_microphone_button = self._small_button(
            selector_row,
            "Actualizar",
            self.refresh_microphones,
        )
        self.refresh_microphone_button.pack(side="left", padx=(9, 0))
        self.microphone_state_label = tk.Label(
            self.microphone_panel,
            textvariable=self.microphone_state_var,
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 8),
        )
        self.microphone_state_label.pack(anchor="w", pady=(3, 0))

        self.settings_divider = tk.Frame(settings, bg=BORDER, height=1)
        self.settings_divider.pack(fill="x", pady=11)
        options_row = tk.Frame(settings, bg=SURFACE)
        options_row.pack(fill="x")
        quality_panel = tk.Frame(options_row, bg=SURFACE)
        quality_panel.pack(side="left", fill="x")
        tk.Label(
            quality_panel,
            text="Calidad de vídeo",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI Semibold", 8),
        ).pack(anchor="w", pady=(0, 4))
        quality_row = tk.Frame(quality_panel, bg=SURFACE)
        quality_row.pack(fill="x")
        self.resolution_box = ttk.Combobox(
            quality_row,
            textvariable=self.resolution_var,
            values=[preset.label for preset in RESOLUTION_PRESETS],
            state="readonly",
            style="Dark.TCombobox",
            width=19,
            font=("Segoe UI", 9),
        )
        self.resolution_box.pack(side="left")
        self.fps_box = ttk.Combobox(
            quality_row,
            textvariable=self.fps_var,
            values=[f"{fps} FPS" for fps in SUPPORTED_FPS],
            state="readonly",
            style="Dark.TCombobox",
            width=10,
            font=("Segoe UI", 9),
        )
        self.fps_box.pack(side="left", padx=(8, 0))

        output_panel = tk.Frame(options_row, bg=SURFACE)
        output_panel.pack(side="right", fill="x", expand=True, padx=(24, 0))
        tk.Label(
            output_panel,
            text="Guardar en",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI Semibold", 8),
        ).pack(anchor="w", pady=(0, 4))
        output_row = tk.Frame(output_panel, bg=SURFACE)
        output_row.pack(fill="x")
        tk.Label(
            output_row,
            textvariable=self.output_path_var,
            bg=SURFACE,
            fg=TEXT,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        self.choose_folder_button = self._small_button(
            output_row,
            "Cambiar",
            self.choose_output_folder,
        )
        self.choose_folder_button.pack(side="right", padx=(8, 0))
        self.open_folder_button = self._small_button(
            output_row,
            "Abrir",
            self.open_output_folder,
        )
        self.open_folder_button.pack(side="right", padx=(8, 0))

        self.record_button = AnimatedActionButton(
            container,
            text=CAPTURE_ACTION[CaptureMode.PRIMARY_SCREEN],
            command=self.toggle_recording,
            width=840,
            height=64,
        )
        self.record_button.pack(fill="x", pady=(13, 6))

        footer = tk.Frame(container, bg=BACKGROUND)
        footer.pack(fill="x")
        self.elapsed_label = tk.Label(
            footer,
            textvariable=self.elapsed_var,
            bg=BACKGROUND,
            fg=TEXT,
            font=("Cascadia Mono", 12, "bold"),
        )
        self.elapsed_label.pack(side="left")
        self.status_label = tk.Label(
            footer,
            textvariable=self.status_var,
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 9),
            justify="right",
            anchor="e",
            wraplength=730,
        )
        self.status_label.pack(side="right", fill="x", expand=True, padx=(14, 0))

    @staticmethod
    def _small_button(
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=SURFACE_HOVER,
            fg=TEXT,
            disabledforeground=SUBTLE,
            activebackground=SURFACE_RAISED,
            activeforeground=TEXT,
            relief="flat",
            borderwidth=0,
            padx=11,
            pady=6,
            cursor="hand2",
            font=("Segoe UI Semibold", 8),
        )

    def _output_path_label(self) -> str:
        home = Path.home()
        try:
            relative = self.output_dir.relative_to(home)
        except ValueError:
            value = str(self.output_dir)
        else:
            value = str(relative)
        if len(value) > 44:
            value = f"…{value[-43:]}"
        return value.replace("\\", "  ·  ")

    @property
    def chrome_process_id(self) -> int | None:
        return self.chrome_process.pid if self.chrome_process is not None else None

    def _selected_capture_mode(self) -> CaptureMode:
        return parse_capture_mode(self.capture_mode_var.get())

    def _select_capture_label(self, label: str) -> None:
        self.capture_mode_var.set(label)
        self._capture_mode_changed()

    def _capture_mode_changed(self) -> None:
        mode = self._selected_capture_mode()
        for label, card in self.capture_mode_cards.items():
            card.set_selected(label == self.capture_mode_var.get())
        self.capture_help_var.set(CAPTURE_HELP[mode])
        if self.recorder.state is RecorderState.IDLE:
            self.record_button.set(text=CAPTURE_ACTION[mode], variant="primary")
        self._update_ready_state()

    def _set_chrome_tone(self, color: str) -> None:
        self.chrome_indicator.itemconfigure("dot", fill=color)
        self.chrome_state_label.configure(fg=color)

    def refresh_chrome(self) -> None:
        if self.recorder.state is not RecorderState.IDLE:
            return
        try:
            self.chrome_process = self.chrome_finder()
        except ProcessDiscoveryError as error:
            self.chrome_process = None
            self.chrome_state_var.set("No se pudo comprobar Chrome")
            self._set_chrome_tone(ERROR)
            self.status_var.set(str(error))
        else:
            if self.chrome_process_id is None:
                self.chrome_state_var.set("Chrome no está abierto")
                self._set_chrome_tone(AMBER)
            else:
                self.chrome_state_var.set("Chrome listo")
                self._set_chrome_tone(GREEN)
        self._update_ready_state()

    def _microphone_option_changed(self) -> None:
        enabled = self.include_microphone_var.get()
        self.waveform_indicator.set_active(enabled)
        if enabled:
            if not self.microphone_panel.winfo_manager():
                self.microphone_panel.pack(
                    fill="x",
                    before=self.settings_divider,
                    pady=(9, 0),
                )
            if not self.microphones and not self.loading_microphones:
                self.refresh_microphones()
        else:
            self.microphone_panel.pack_forget()
            self.microphone_state_var.set("El micrófono está desactivado")
        self._update_ready_state()

    def refresh_microphones(self) -> None:
        if self.recorder.state is not RecorderState.IDLE or self.loading_microphones:
            return
        self.loading_microphones = True
        self.refresh_microphone_button.configure(state="disabled")
        self.microphone_state_var.set("Comprobando micrófonos…")
        self._update_ready_state()

        def worker() -> None:
            try:
                microphones = self.client.list_microphones()
            except FFmpegError as error:
                self._schedule_ui(lambda error=error: self._microphones_failed(error))
            else:
                self._schedule_ui(lambda: self._microphones_loaded(microphones))

        threading.Thread(target=worker, name="microphone-discovery", daemon=True).start()

    def _schedule_ui(self, callback: Callable[[], None]) -> None:
        try:
            self.root.after(0, callback)
        except (RuntimeError, tk.TclError):
            return

    def _microphones_loaded(self, microphones: list[Microphone]) -> None:
        self.loading_microphones = False
        self.microphones = microphones
        self.microphone_box.configure(values=[item.name for item in microphones])
        self.refresh_microphone_button.configure(state="normal")
        if microphones:
            self.microphone_box.current(0)
            self.microphone_state_var.set("Micrófono preparado")
            self.microphone_state_label.configure(fg=GREEN)
        else:
            self.microphone_var.set("")
            self.microphone_state_var.set("No se ha detectado ningún micrófono")
            self.microphone_state_label.configure(fg=ERROR)
        self._update_ready_state()

    def _microphones_failed(self, error: Exception) -> None:
        self.loading_microphones = False
        self.refresh_microphone_button.configure(state="normal")
        self.microphone_state_var.set("No se pudo comprobar el micrófono")
        self.microphone_state_label.configure(fg=ERROR)
        self.status_var.set(str(error))
        self._update_ready_state()

    def _microphone_selected(self, _event: object = None) -> None:
        self.microphone_state_var.set("Micrófono preparado")
        self.microphone_state_label.configure(fg=GREEN)
        self._update_ready_state()

    def _selected_microphone(self) -> Microphone | None:
        return next(
            (item for item in self.microphones if item.name == self.microphone_var.get()),
            None,
        )

    def _update_ready_state(self) -> None:
        if self.recorder.state is not RecorderState.IDLE:
            return
        microphone_ready = (
            not self.include_microphone_var.get()
            or self._selected_microphone() is not None
        )
        ready = self.chrome_process_id is not None and microphone_ready
        self.record_button.set(state="normal" if ready else "disabled")
        if self.chrome_process_id is None:
            self.hero_status_var.set("ABRE CHROME")
            self.orbital_recorder.set_state("error")
            self.status_var.set("Abre Chrome con la conferencia y vuelve a comprobar.")
            return
        if not microphone_ready:
            self.hero_status_var.set("REVISA EL MICRÓFONO")
            self.orbital_recorder.set_state("error")
            self.status_var.set("Selecciona un micrófono o desactiva la opción.")
            return

        self.hero_status_var.set("LISTO PARA GRABAR")
        self.orbital_recorder.set_state("ready")
        mode = self._selected_capture_mode()
        microphone = " + micrófono" if self.include_microphone_var.get() else ""
        source = {
            CaptureMode.PRIMARY_SCREEN: "pantalla completa · audio de Chrome",
            CaptureMode.SELECTED_MONITOR: "elige una pantalla · audio de Chrome",
            CaptureMode.CHROME_TAB: "elige una pestaña · audio de la pestaña",
        }[mode]
        self.status_var.set(f"Preparado: {source}{microphone}.")

    def _set_quality_controls_state(self, state: str) -> None:
        self.resolution_box.configure(state=state)
        self.fps_box.configure(state=state)

    def _set_idle_controls(self) -> None:
        self.microphone_toggle.set_enabled(True)
        self.refresh_chrome_button.configure(state="normal")
        for card in self.capture_mode_buttons:
            card.set_enabled(True)
        self._set_quality_controls_state("readonly")
        self.microphone_box.configure(state="readonly")
        self.refresh_microphone_button.configure(state="normal")
        self.choose_folder_button.configure(state="normal")
        self._update_ready_state()

    def _set_busy_controls(self) -> None:
        self.microphone_toggle.set_enabled(False)
        self.refresh_chrome_button.configure(state="disabled")
        self.microphone_box.configure(state="disabled")
        self.refresh_microphone_button.configure(state="disabled")
        self.choose_folder_button.configure(state="disabled")
        for card in self.capture_mode_buttons:
            card.set_enabled(False)
        self._set_quality_controls_state("disabled")

    def toggle_recording(self) -> None:
        if self.recorder.state is RecorderState.IDLE:
            self._start_recording()
        elif self.recorder.state is RecorderState.RECORDING:
            self._stop_recording()

    def _start_recording(self) -> None:
        self.refresh_chrome()
        if self.chrome_process_id is None:
            messagebox.showwarning(
                "Chrome no está abierto",
                "Abre Chrome con la conferencia antes de empezar.",
                parent=self.root,
            )
            return
        microphone = self._selected_microphone()
        try:
            config = build_recording_config(
                self.output_dir,
                self.chrome_process_id,
                self.include_microphone_var.get(),
                microphone,
                self.resolution_var.get(),
                self.fps_var.get(),
                self.capture_mode_var.get(),
            )
        except ValueError as error:
            messagebox.showerror("Configuración no válida", str(error), parent=self.root)
            return

        self.record_button.set(state="disabled", text="Preparando…")
        self._set_busy_controls()
        self.hero_status_var.set("PREPARANDO CAPTURA")
        self.orbital_recorder.set_state("busy")
        if self._selected_capture_mode() is CaptureMode.PRIMARY_SCREEN:
            self.status_var.set("Preparando el audio de Chrome y la captura de pantalla…")
        else:
            self.status_var.set("Abriendo el selector nativo de Chrome…")

        def worker() -> None:
            try:
                chrome_executable = (
                    self.chrome_process.executable
                    if self.chrome_process is not None
                    else None
                )
                video_path = self.recorder.start(config, chrome_executable)
            except (RecorderError, OSError) as error:
                self._schedule_ui(lambda error=error: self._start_failed(error))
            else:
                self._schedule_ui(lambda: self._recording_started(video_path))

        threading.Thread(target=worker, name="recording-start", daemon=True).start()

    def _recording_started(self, video_path: Path) -> None:
        self.current_video = video_path
        self.started_at = time.monotonic()
        self.elapsed_var.set("00:00")
        self.record_button.set(
            state="normal",
            text="Finalizar y guardar",
            variant="danger",
        )
        self.hero_status_var.set("GRABANDO")
        self.orbital_recorder.set_state("recording")
        microphone = " y micrófono" if self.include_microphone_var.get() else ""
        source = {
            CaptureMode.PRIMARY_SCREEN: "la pantalla completa",
            CaptureMode.SELECTED_MONITOR: "la pantalla seleccionada",
            CaptureMode.CHROME_TAB: "la pestaña seleccionada",
        }[self._selected_capture_mode()]
        self.status_var.set(
            f"Grabando {source}, Chrome{microphone}. Vuelve aquí para finalizar."
        )
        self.root.after(700, self.root.iconify)
        self._tick()

    def _start_failed(self, error: Exception) -> None:
        self.record_button.set(
            text=CAPTURE_ACTION[self._selected_capture_mode()],
            variant="primary",
        )
        self._set_idle_controls()
        self.hero_status_var.set("NO SE PUDO GRABAR")
        self.orbital_recorder.set_state("error")
        self.status_var.set(str(error))
        messagebox.showerror("No se pudo iniciar la grabación", str(error), parent=self.root)

    def _tick(self) -> None:
        if self.recorder.state is not RecorderState.RECORDING:
            return
        self.elapsed_var.set(format_elapsed(time.monotonic() - self.started_at))
        if self.recorder.poll() is not None:
            self.status_var.set("Una captura se ha detenido; protegiendo los temporales…")
            self._stop_recording()
            return
        self.root.after(250, self._tick)

    def _stop_recording(self) -> None:
        if self.recorder.state is not RecorderState.RECORDING:
            return
        self.root.deiconify()
        self.root.lift()
        self.record_button.set(state="disabled", text="Finalizando…")
        self.hero_status_var.set("GUARDANDO VÍDEO")
        self.orbital_recorder.set_state("busy")
        self.status_var.set("Combinando vídeo y audio. No cierres la aplicación…")

        def worker() -> None:
            try:
                video_path = self.recorder.stop()
            except RecorderError as error:
                self._schedule_ui(lambda error=error: self._stop_failed(error))
            else:
                self._schedule_ui(lambda: self._recording_saved(video_path))

        threading.Thread(target=worker, name="recording-stop", daemon=True).start()

    def _recording_saved(self, video_path: Path) -> None:
        self.current_video = video_path
        self.record_button.set(
            text="Grabar otra conferencia",
            variant="primary",
        )
        self._set_idle_controls()
        self.hero_status_var.set("VÍDEO GUARDADO")
        self.orbital_recorder.set_state("saved")
        self.status_var.set(f"Vídeo guardado: {video_path.name}")
        if self.close_after_stop:
            self.root.destroy()

    def _stop_failed(self, error: Exception) -> None:
        self.record_button.set(text="Volver a intentar", variant="primary")
        self._set_idle_controls()
        self.hero_status_var.set("GRABACIÓN INTERRUMPIDA")
        self.orbital_recorder.set_state("error")
        self.status_var.set("La grabación ha fallado; se han conservado los temporales.")
        messagebox.showerror("No se pudo finalizar", str(error), parent=self.root)
        if self.close_after_stop:
            self.root.destroy()

    def choose_output_folder(self) -> None:
        if self.recorder.state is not RecorderState.IDLE:
            return
        selected = self.directory_chooser(
            title="Elegir carpeta para las grabaciones",
            initialdir=str(self.output_dir),
            parent=self.root,
        )
        if not selected:
            return
        self.output_dir = Path(selected)
        self.output_path_var.set(self._output_path_label())
        self.status_var.set(f"Las grabaciones se guardarán en {self.output_dir}.")

    def open_output_folder(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(self.output_dir)  # type: ignore[attr-defined]

    def _on_close(self) -> None:
        if self.recorder.state is RecorderState.RECORDING:
            if messagebox.askyesno(
                "¿Finalizar la grabación?",
                "¿Quieres finalizarla, guardarla y salir?",
                parent=self.root,
            ):
                self.close_after_stop = True
                self._stop_recording()
            return
        if self.recorder.state is RecorderState.STOPPING:
            messagebox.showinfo(
                "Finalizando el vídeo",
                "Espera unos segundos mientras se combina y se guarda.",
                parent=self.root,
            )
            return
        self.root.destroy()
