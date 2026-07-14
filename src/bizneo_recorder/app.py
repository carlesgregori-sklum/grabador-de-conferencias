from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .ffmpeg import FFmpegClient, FFmpegError
from .models import Microphone, RecordingConfig
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
BORDER = "#D0D5DD"


def format_elapsed(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    minutes, seconds_part = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds_part:02d}"


class BizneoRecorderApp:
    """Small, keyboard-friendly Tk interface for one recording at a time."""

    def __init__(
        self,
        root: tk.Tk,
        client: FFmpegClient,
        recorder: Recorder,
    ) -> None:
        self.root = root
        self.client = client
        self.recorder = recorder
        self.output_dir = Path.home() / "Videos" / "Bizneo Recorder"
        self.microphones: list[Microphone] = []
        self.started_at = 0.0
        self.current_video: Path | None = None
        self.close_after_stop = False

        self.status_var = tk.StringVar(value="Buscant micròfons…")
        self.microphone_state_var = tk.StringVar(value="● Comprovant micròfon")
        self.elapsed_var = tk.StringVar(value="00:00")
        self.microphone_var = tk.StringVar()

        self._configure_window()
        self._build_interface()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Escape>", lambda _event: self._on_close())
        self.refresh_microphones()

    def _configure_window(self) -> None:
        self.root.title("Bizneo Recorder")
        self.root.geometry("620x500")
        self.root.minsize(620, 500)
        self.root.maxsize(620, 500)
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
            padding=8,
            font=("Segoe UI", 10),
        )

    def _build_interface(self) -> None:
        container = tk.Frame(self.root, bg=BACKGROUND, padx=28, pady=24)
        container.pack(fill="both", expand=True)

        header = tk.Frame(container, bg=BACKGROUND)
        header.pack(fill="x")
        tk.Label(
            header,
            text="Bizneo Recorder",
            bg=BACKGROUND,
            fg=TEXT,
            font=("Segoe UI Semibold", 22),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Grava la pantalla Full HD i la teua veu en un MP4.",
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 18))

        card = tk.Frame(
            container,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=22,
            pady=20,
        )
        card.pack(fill="x")

        tk.Label(
            card,
            text="Micròfon",
            bg=SURFACE,
            fg=TEXT,
            font=("Segoe UI Semibold", 10),
        ).pack(anchor="w")

        selector_row = tk.Frame(card, bg=SURFACE)
        selector_row.pack(fill="x", pady=(7, 4))
        self.microphone_box = ttk.Combobox(
            selector_row,
            textvariable=self.microphone_var,
            state="readonly",
            style="Recorder.TCombobox",
            font=("Segoe UI", 10),
        )
        self.microphone_box.pack(side="left", fill="x", expand=True)
        self.microphone_box.bind("<<ComboboxSelected>>", self._microphone_selected)

        self.refresh_button = tk.Button(
            selector_row,
            text="Actualitzar",
            command=self.refresh_microphones,
            bg="#EEF2FF",
            fg=PRIMARY,
            activebackground="#E0E7FF",
            activeforeground=PRIMARY_ACTIVE,
            relief="flat",
            borderwidth=0,
            padx=13,
            pady=9,
            cursor="hand2",
            font=("Segoe UI Semibold", 9),
        )
        self.refresh_button.pack(side="left", padx=(10, 0))

        self.microphone_state_label = tk.Label(
            card,
            textvariable=self.microphone_state_var,
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 9),
        )
        self.microphone_state_label.pack(anchor="w", pady=(2, 16))

        tk.Label(
            card,
            text="Els vídeos es guardaran en",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w")
        tk.Label(
            card,
            text=str(self.output_dir),
            bg=SURFACE,
            fg=TEXT,
            font=("Segoe UI", 9),
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        recording_row = tk.Frame(container, bg=BACKGROUND)
        recording_row.pack(fill="x", pady=(22, 10))
        self.record_button = tk.Button(
            recording_row,
            text="Començar gravació",
            command=self.toggle_recording,
            state="disabled",
            bg=PRIMARY,
            fg="white",
            disabledforeground="#EAECF0",
            activebackground=PRIMARY_ACTIVE,
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            padx=22,
            pady=13,
            cursor="hand2",
            font=("Segoe UI Semibold", 11),
        )
        self.record_button.pack(side="left")

        self.elapsed_label = tk.Label(
            recording_row,
            textvariable=self.elapsed_var,
            bg=BACKGROUND,
            fg=TEXT,
            font=("Consolas", 20, "bold"),
        )
        self.elapsed_label.pack(side="right")

        self.status_label = tk.Label(
            container,
            textvariable=self.status_var,
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=560,
        )
        self.status_label.pack(fill="x", pady=(2, 10))

        self.open_folder_button = tk.Button(
            container,
            text="Obrir carpeta de vídeos",
            command=self.open_output_folder,
            state="disabled",
            bg=BACKGROUND,
            fg=PRIMARY,
            activebackground=BACKGROUND,
            activeforeground=PRIMARY_ACTIVE,
            relief="flat",
            borderwidth=0,
            padx=0,
            pady=4,
            cursor="hand2",
            font=("Segoe UI Semibold", 9, "underline"),
        )
        self.open_folder_button.pack(anchor="w")

    def refresh_microphones(self) -> None:
        if self.recorder.state is not RecorderState.IDLE:
            return
        self.refresh_button.configure(state="disabled")
        self.record_button.configure(state="disabled")
        self.microphone_state_var.set("● Comprovant micròfon")
        self.microphone_state_label.configure(fg=MUTED)
        self.status_var.set("Buscant micròfons disponibles…")

        def worker() -> None:
            try:
                microphones = self.client.list_microphones()
            except FFmpegError as error:
                self.root.after(0, lambda error=error: self._microphones_failed(error))
            else:
                self.root.after(0, lambda: self._microphones_loaded(microphones))

        threading.Thread(target=worker, name="microphone-discovery", daemon=True).start()

    def _microphones_loaded(self, microphones: list[Microphone]) -> None:
        self.microphones = microphones
        self.microphone_box.configure(values=[item.name for item in microphones])
        self.refresh_button.configure(state="normal")
        if not microphones:
            self.microphone_var.set("")
            self.microphone_state_var.set("● No s'ha detectat cap micròfon")
            self.microphone_state_label.configure(fg=DANGER)
            self.status_var.set(
                "Connecta o activa un micròfon i revisa Configuració > Privacitat > Micròfon."
            )
            return

        self.microphone_box.current(0)
        self.microphone_state_var.set("● Micròfon preparat")
        self.microphone_state_label.configure(fg=SUCCESS)
        self.status_var.set("Preparat. En començar, la finestra es minimitzarà automàticament.")
        self.record_button.configure(state="normal")

    def _microphones_failed(self, error: Exception) -> None:
        self.refresh_button.configure(state="normal")
        self.microphone_state_var.set("● No s'ha pogut comprovar el micròfon")
        self.microphone_state_label.configure(fg=DANGER)
        self.status_var.set(str(error))
        messagebox.showerror("No es pot iniciar", str(error), parent=self.root)

    def _microphone_selected(self, _event: object = None) -> None:
        self.microphone_state_var.set("● Micròfon preparat")
        self.microphone_state_label.configure(fg=SUCCESS)

    def toggle_recording(self) -> None:
        if self.recorder.state is RecorderState.IDLE:
            self._start_recording()
        elif self.recorder.state is RecorderState.RECORDING:
            self._stop_recording()

    def _start_recording(self) -> None:
        microphone = next(
            (item for item in self.microphones if item.name == self.microphone_var.get()),
            None,
        )
        if microphone is None:
            messagebox.showwarning(
                "Tria un micròfon",
                "Selecciona un micròfon abans de començar.",
                parent=self.root,
            )
            return

        config = RecordingConfig(microphone, self.output_dir)
        self.record_button.configure(state="disabled", text="Iniciant…")
        self.microphone_box.configure(state="disabled")
        self.refresh_button.configure(state="disabled")
        self.status_var.set("Preparant la gravació Full HD…")

        def worker() -> None:
            try:
                video_path = self.recorder.start(config)
            except (RecorderError, OSError) as error:
                self.root.after(0, lambda error=error: self._start_failed(error))
            else:
                self.root.after(0, lambda: self._recording_started(video_path))

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
        self.status_var.set("Gravant pantalla i veu. Torna a esta finestra per finalitzar.")
        self.root.after(700, self.root.iconify)
        self._tick()

    def _start_failed(self, error: Exception) -> None:
        self.record_button.configure(
            state="normal" if self.microphones else "disabled",
            text="Començar gravació",
            bg=PRIMARY,
            activebackground=PRIMARY_ACTIVE,
        )
        self.microphone_box.configure(state="readonly")
        self.refresh_button.configure(state="normal")
        self.status_var.set(str(error))
        messagebox.showerror("No s'ha pogut gravar", str(error), parent=self.root)

    def _tick(self) -> None:
        if self.recorder.state is not RecorderState.RECORDING:
            return
        self.elapsed_var.set(format_elapsed(time.monotonic() - self.started_at))
        if self.recorder.poll() is not None:
            self.status_var.set("FFmpeg s'ha aturat; finalitzant el fitxer…")
            self._stop_recording()
            return
        self.root.after(250, self._tick)

    def _stop_recording(self) -> None:
        if self.recorder.state is not RecorderState.RECORDING:
            return
        self.root.deiconify()
        self.root.lift()
        self.record_button.configure(state="disabled", text="Finalitzant…")
        self.status_var.set("Tancant el vídeo correctament. No tanques l'aplicació…")

        def worker() -> None:
            try:
                video_path = self.recorder.stop()
            except RecorderError as error:
                self.root.after(0, lambda error=error: self._stop_failed(error))
            else:
                self.root.after(0, lambda: self._recording_saved(video_path))

        threading.Thread(target=worker, name="recording-stop", daemon=True).start()

    def _recording_saved(self, video_path: Path) -> None:
        self.current_video = video_path
        self.record_button.configure(
            state="normal",
            text="Començar una altra gravació",
            bg=PRIMARY,
            activebackground=PRIMARY_ACTIVE,
        )
        self.microphone_box.configure(state="readonly")
        self.refresh_button.configure(state="normal")
        self.open_folder_button.configure(state="normal")
        self.status_var.set(f"Vídeo guardat correctament: {video_path.name}")
        if self.close_after_stop:
            self.root.destroy()

    def _stop_failed(self, error: Exception) -> None:
        self.record_button.configure(
            state="normal",
            text="Començar una altra gravació",
            bg=PRIMARY,
            activebackground=PRIMARY_ACTIVE,
        )
        self.microphone_box.configure(state="readonly")
        self.refresh_button.configure(state="normal")
        self.open_folder_button.configure(state="normal")
        self.status_var.set("La gravació ha fallat; s'ha conservat el fitxer temporal.")
        messagebox.showerror("No s'ha pogut finalitzar", str(error), parent=self.root)
        if self.close_after_stop:
            self.root.destroy()

    def open_output_folder(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(self.output_dir)  # type: ignore[attr-defined]

    def _on_close(self) -> None:
        if self.recorder.state is RecorderState.RECORDING:
            should_stop = messagebox.askyesno(
                "Finalitzar la gravació?",
                "Hi ha una gravació en marxa. Vols finalitzar-la, guardar-la i eixir?",
                parent=self.root,
            )
            if should_stop:
                self.close_after_stop = True
                self._stop_recording()
            return
        if self.recorder.state is RecorderState.STOPPING:
            messagebox.showinfo(
                "Finalitzant vídeo",
                "Espera uns segons mentre es guarda el vídeo.",
                parent=self.root,
            )
            return
        self.root.destroy()

