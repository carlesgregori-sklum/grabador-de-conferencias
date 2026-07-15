from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk

from .ffmpeg import FFmpegClient, FFmpegError
from .models import (
    RESOLUTION_PRESETS,
    SUPPORTED_FPS,
    Microphone,
    RecordingConfig,
    get_resolution_preset,
    parse_fps,
)
from .processes import ProcessDiscoveryError, find_chrome_root
from .recorder import Recorder, RecorderError, RecorderState


BACKGROUND = "#F4F6FA"
SURFACE = "#FFFFFF"
TEXT = "#172033"
MUTED = "#667085"
PRIMARY = "#3155D9"
PRIMARY_ACTIVE = "#2444B8"
DANGER = "#D92D20"
DANGER_ACTIVE = "#B42318"
SUCCESS = "#067647"
WARNING = "#B54708"
BORDER = "#D0D5DD"


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
) -> RecordingConfig:
    if include_microphone and microphone is None:
        raise ValueError("activa i selecciona un micròfon o desactiva l'opció")
    preset = get_resolution_preset(resolution_label)
    return RecordingConfig(
        output_dir,
        chrome_process_id,
        microphone=microphone if include_microphone else None,
        width=preset.width,
        height=preset.height,
        fps=parse_fps(fps_label),
    )


class BizneoRecorderApp:
    """Minimal conference UI for full-screen video and Chrome-only audio."""

    def __init__(
        self,
        root: tk.Tk,
        client: FFmpegClient,
        recorder: Recorder,
        chrome_finder: Callable[[], int | None] = find_chrome_root,
    ) -> None:
        self.root = root
        self.client = client
        self.recorder = recorder
        self.chrome_finder = chrome_finder
        self.output_dir = Path.home() / "Videos" / "Conference Recorder"
        self.chrome_process_id: int | None = None
        self.microphones: list[Microphone] = []
        self.started_at = 0.0
        self.current_video: Path | None = None
        self.close_after_stop = False
        self.loading_microphones = False

        self.status_var = tk.StringVar(value="Comprovant Chrome…")
        self.chrome_state_var = tk.StringVar(value="● Comprovant Chrome")
        self.elapsed_var = tk.StringVar(value="00:00")
        self.include_microphone_var = tk.BooleanVar(value=False)
        self.microphone_var = tk.StringVar()
        self.microphone_state_var = tk.StringVar(value="El micròfon està desactivat")
        self.resolution_var = tk.StringVar(value="Full HD 1080p")
        self.fps_var = tk.StringVar(value="30 FPS")

        self._configure_window()
        self._build_interface()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Escape>", lambda _event: self._on_close())
        self.refresh_chrome()

    def _configure_window(self) -> None:
        self.root.title("Conference Recorder")
        self.root.geometry("580x650")
        self.root.minsize(580, 650)
        self.root.maxsize(580, 650)
        self.root.configure(bg=BACKGROUND)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Recorder.TCombobox",
            fieldbackground=SURFACE,
            background=SURFACE,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=7,
            font=("Segoe UI", 10),
        )

    def _build_interface(self) -> None:
        container = tk.Frame(self.root, bg=BACKGROUND, padx=28, pady=24)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text="Conference Recorder",
            bg=BACKGROUND,
            fg=TEXT,
            font=("Segoe UI Semibold", 22),
        ).pack(anchor="w")
        tk.Label(
            container,
            text="Grava tota la pantalla i l'àudio de Chrome en un MP4.",
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 18))

        card = tk.Frame(
            container,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=20,
            pady=18,
        )
        card.pack(fill="x")

        chrome_row = tk.Frame(card, bg=SURFACE)
        chrome_row.pack(fill="x")
        self.chrome_state_label = tk.Label(
            chrome_row,
            textvariable=self.chrome_state_var,
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI Semibold", 10),
        )
        self.chrome_state_label.pack(side="left")
        self.refresh_chrome_button = tk.Button(
            chrome_row,
            text="Tornar a comprovar",
            command=self.refresh_chrome,
            bg=SURFACE,
            fg=PRIMARY,
            activebackground=SURFACE,
            activeforeground=PRIMARY_ACTIVE,
            relief="flat",
            borderwidth=0,
            padx=0,
            cursor="hand2",
            font=("Segoe UI Semibold", 9, "underline"),
        )
        self.refresh_chrome_button.pack(side="right")

        separator = tk.Frame(card, bg="#EAECF0", height=1)
        separator.pack(fill="x", pady=15)

        self.microphone_toggle = tk.Checkbutton(
            card,
            text="Incloure el meu micròfon",
            variable=self.include_microphone_var,
            command=self._microphone_option_changed,
            bg=SURFACE,
            fg=TEXT,
            activebackground=SURFACE,
            activeforeground=TEXT,
            selectcolor=SURFACE,
            anchor="w",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI Semibold", 10),
        )
        self.microphone_toggle.pack(fill="x")

        self.microphone_panel = tk.Frame(card, bg=SURFACE)
        selector_row = tk.Frame(self.microphone_panel, bg=SURFACE)
        selector_row.pack(fill="x", pady=(8, 3))
        self.microphone_box = ttk.Combobox(
            selector_row,
            textvariable=self.microphone_var,
            state="readonly",
            style="Recorder.TCombobox",
            font=("Segoe UI", 10),
        )
        self.microphone_box.pack(side="left", fill="x", expand=True)
        self.microphone_box.bind("<<ComboboxSelected>>", self._microphone_selected)
        self.refresh_microphone_button = tk.Button(
            selector_row,
            text="Actualitzar",
            command=self.refresh_microphones,
            bg="#EEF2FF",
            fg=PRIMARY,
            activebackground="#E0E7FF",
            activeforeground=PRIMARY_ACTIVE,
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=8,
            cursor="hand2",
            font=("Segoe UI Semibold", 9),
        )
        self.refresh_microphone_button.pack(side="left", padx=(9, 0))
        self.microphone_state_label = tk.Label(
            self.microphone_panel,
            textvariable=self.microphone_state_var,
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 9),
        )
        self.microphone_state_label.pack(anchor="w")

        options_label = tk.Label(
            card,
            text="Opcions de vídeo",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI Semibold", 9),
        )
        options_label.pack(anchor="w", pady=(18, 6))
        quality_row = tk.Frame(card, bg=SURFACE)
        quality_row.pack(fill="x")
        self.resolution_box = ttk.Combobox(
            quality_row,
            textvariable=self.resolution_var,
            values=[preset.label for preset in RESOLUTION_PRESETS],
            state="readonly",
            style="Recorder.TCombobox",
            font=("Segoe UI", 10),
        )
        self.resolution_box.pack(side="left", fill="x", expand=True)
        self.fps_box = ttk.Combobox(
            quality_row,
            textvariable=self.fps_var,
            values=[f"{fps} FPS" for fps in SUPPORTED_FPS],
            state="readonly",
            style="Recorder.TCombobox",
            width=12,
            font=("Segoe UI", 10),
        )
        self.fps_box.pack(side="left", padx=(10, 0))

        tk.Label(
            card,
            text="Els vídeos es guarden en Vídeos\\Conference Recorder",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(14, 0))

        self.record_button = tk.Button(
            container,
            text="Gravar conferència",
            command=self.toggle_recording,
            state="disabled",
            bg=PRIMARY,
            fg="white",
            disabledforeground="#EAECF0",
            activebackground=PRIMARY_ACTIVE,
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            pady=14,
            cursor="hand2",
            font=("Segoe UI Semibold", 11),
        )
        self.record_button.pack(fill="x", pady=(20, 10))

        self.elapsed_label = tk.Label(
            container,
            textvariable=self.elapsed_var,
            bg=BACKGROUND,
            fg=TEXT,
            font=("Consolas", 20, "bold"),
        )
        self.elapsed_label.pack()
        self.status_label = tk.Label(
            container,
            textvariable=self.status_var,
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 9),
            justify="center",
            wraplength=510,
        )
        self.status_label.pack(fill="x", pady=(3, 6))
        self.open_folder_button = tk.Button(
            container,
            text="Obrir carpeta de vídeos",
            command=self.open_output_folder,
            bg=BACKGROUND,
            fg=PRIMARY,
            activebackground=BACKGROUND,
            activeforeground=PRIMARY_ACTIVE,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI Semibold", 9, "underline"),
        )
        self.open_folder_button.pack()

    def refresh_chrome(self) -> None:
        if self.recorder.state is not RecorderState.IDLE:
            return
        try:
            self.chrome_process_id = self.chrome_finder()
        except ProcessDiscoveryError as error:
            self.chrome_process_id = None
            self.chrome_state_var.set("● No s'ha pogut comprovar Chrome")
            self.chrome_state_label.configure(fg=DANGER)
            self.status_var.set(str(error))
        else:
            if self.chrome_process_id is None:
                self.chrome_state_var.set("● Chrome no està obert")
                self.chrome_state_label.configure(fg=WARNING)
            else:
                self.chrome_state_var.set("● Chrome detectat · àudio preparat")
                self.chrome_state_label.configure(fg=SUCCESS)
        self._update_ready_state()

    def _microphone_option_changed(self) -> None:
        if self.include_microphone_var.get():
            if not self.microphone_panel.winfo_manager():
                self.microphone_panel.pack(
                    fill="x",
                    after=self.microphone_toggle,
                    pady=(2, 0),
                )
            if not self.microphones and not self.loading_microphones:
                self.refresh_microphones()
        else:
            self.microphone_panel.pack_forget()
            self.microphone_state_var.set("El micròfon està desactivat")
        self._update_ready_state()

    def refresh_microphones(self) -> None:
        if self.recorder.state is not RecorderState.IDLE or self.loading_microphones:
            return
        self.loading_microphones = True
        self.refresh_microphone_button.configure(state="disabled")
        self.microphone_state_var.set("Comprovant micròfons…")
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
            # The window can be destroyed while a short worker is finishing.
            return

    def _microphones_loaded(self, microphones: list[Microphone]) -> None:
        self.loading_microphones = False
        self.microphones = microphones
        self.microphone_box.configure(values=[item.name for item in microphones])
        self.refresh_microphone_button.configure(state="normal")
        if microphones:
            self.microphone_box.current(0)
            self.microphone_state_var.set("Micròfon preparat")
            self.microphone_state_label.configure(fg=SUCCESS)
        else:
            self.microphone_var.set("")
            self.microphone_state_var.set("No s'ha detectat cap micròfon")
            self.microphone_state_label.configure(fg=DANGER)
        self._update_ready_state()

    def _microphones_failed(self, error: Exception) -> None:
        self.loading_microphones = False
        self.refresh_microphone_button.configure(state="normal")
        self.microphone_state_var.set("No s'ha pogut comprovar el micròfon")
        self.microphone_state_label.configure(fg=DANGER)
        self.status_var.set(str(error))
        self._update_ready_state()

    def _microphone_selected(self, _event: object = None) -> None:
        self.microphone_state_var.set("Micròfon preparat")
        self.microphone_state_label.configure(fg=SUCCESS)
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
        self.record_button.configure(state="normal" if ready else "disabled")
        if self.chrome_process_id is None:
            self.status_var.set("Obri Chrome amb la conferència i torna a comprovar.")
        elif not microphone_ready:
            self.status_var.set("Selecciona un micròfon o desactiva l'opció.")
        else:
            sources = "Chrome + micròfon" if self.include_microphone_var.get() else "Chrome"
            self.status_var.set(
                f"Preparat: pantalla completa · àudio de {sources}."
            )

    def _set_quality_controls_state(self, state: str) -> None:
        self.resolution_box.configure(state=state)
        self.fps_box.configure(state=state)

    def _set_idle_controls(self) -> None:
        self.microphone_toggle.configure(state="normal")
        self.refresh_chrome_button.configure(state="normal")
        self._set_quality_controls_state("readonly")
        self.microphone_box.configure(state="readonly")
        self.refresh_microphone_button.configure(state="normal")
        self._update_ready_state()

    def toggle_recording(self) -> None:
        if self.recorder.state is RecorderState.IDLE:
            self._start_recording()
        elif self.recorder.state is RecorderState.RECORDING:
            self._stop_recording()

    def _start_recording(self) -> None:
        self.refresh_chrome()
        if self.chrome_process_id is None:
            messagebox.showwarning(
                "Chrome no està obert",
                "Obri Chrome amb la conferència abans de començar.",
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
            )
        except ValueError as error:
            messagebox.showerror("Configuració no vàlida", str(error), parent=self.root)
            return

        self.record_button.configure(state="disabled", text="Preparant…")
        self.microphone_toggle.configure(state="disabled")
        self.refresh_chrome_button.configure(state="disabled")
        self.microphone_box.configure(state="disabled")
        self.refresh_microphone_button.configure(state="disabled")
        self._set_quality_controls_state("disabled")
        self.status_var.set("Preparant àudio de Chrome i captura de pantalla…")

        def worker() -> None:
            try:
                video_path = self.recorder.start(config)
            except (RecorderError, OSError) as error:
                self._schedule_ui(lambda error=error: self._start_failed(error))
            else:
                self._schedule_ui(lambda: self._recording_started(video_path))

        threading.Thread(target=worker, name="recording-start", daemon=True).start()

    def _recording_started(self, video_path: Path) -> None:
        self.current_video = video_path
        self.started_at = time.monotonic()
        self.elapsed_var.set("00:00")
        self.record_button.configure(
            state="normal",
            text="Finalitzar i guardar",
            bg=DANGER,
            activebackground=DANGER_ACTIVE,
        )
        microphone = " i micròfon" if self.include_microphone_var.get() else ""
        self.status_var.set(
            f"Gravant tota la pantalla, Chrome{microphone}. Torna ací per finalitzar."
        )
        self.root.after(700, self.root.iconify)
        self._tick()

    def _start_failed(self, error: Exception) -> None:
        self.record_button.configure(
            text="Gravar conferència",
            bg=PRIMARY,
            activebackground=PRIMARY_ACTIVE,
        )
        self._set_idle_controls()
        self.status_var.set(str(error))
        messagebox.showerror("No s'ha pogut gravar", str(error), parent=self.root)

    def _tick(self) -> None:
        if self.recorder.state is not RecorderState.RECORDING:
            return
        self.elapsed_var.set(format_elapsed(time.monotonic() - self.started_at))
        if self.recorder.poll() is not None:
            self.status_var.set("Una captura s'ha aturat; protegint els temporals…")
            self._stop_recording()
            return
        self.root.after(250, self._tick)

    def _stop_recording(self) -> None:
        if self.recorder.state is not RecorderState.RECORDING:
            return
        self.root.deiconify()
        self.root.lift()
        self.record_button.configure(state="disabled", text="Finalitzant…")
        self.status_var.set("Combinant vídeo i àudio. No tanques l'aplicació…")

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
        self.record_button.configure(
            text="Gravar una altra conferència",
            bg=PRIMARY,
            activebackground=PRIMARY_ACTIVE,
        )
        self._set_idle_controls()
        self.status_var.set(f"Vídeo guardat: {video_path.name}")
        if self.close_after_stop:
            self.root.destroy()

    def _stop_failed(self, error: Exception) -> None:
        self.record_button.configure(
            text="Tornar a intentar",
            bg=PRIMARY,
            activebackground=PRIMARY_ACTIVE,
        )
        self._set_idle_controls()
        self.status_var.set("La gravació ha fallat; s'han conservat els temporals.")
        messagebox.showerror("No s'ha pogut finalitzar", str(error), parent=self.root)
        if self.close_after_stop:
            self.root.destroy()

    def open_output_folder(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(self.output_dir)  # type: ignore[attr-defined]

    def _on_close(self) -> None:
        if self.recorder.state is RecorderState.RECORDING:
            if messagebox.askyesno(
                "Finalitzar la gravació?",
                "Vols finalitzar-la, guardar-la i eixir?",
                parent=self.root,
            ):
                self.close_after_stop = True
                self._stop_recording()
            return
        if self.recorder.state is RecorderState.STOPPING:
            messagebox.showinfo(
                "Finalitzant vídeo",
                "Espera uns segons mentre es combina i es guarda.",
                parent=self.root,
            )
            return
        self.root.destroy()
