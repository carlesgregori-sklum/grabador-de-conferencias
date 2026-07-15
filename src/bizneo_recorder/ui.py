from __future__ import annotations

import math
import time
import tkinter as tk
from collections.abc import Callable


BACKGROUND = "#0B0C10"
SURFACE = "#151720"
SURFACE_HOVER = "#1B1E29"
SURFACE_RAISED = "#202330"
TEXT = "#F7F7FA"
MUTED = "#9CA3B5"
SUBTLE = "#686F82"
BORDER = "#2A2E3A"
CORAL = "#FF5A5F"
CORAL_DARK = "#C83F48"
VIOLET = "#8B5CF6"
GREEN = "#55E6A5"
AMBER = "#F6B94A"
ERROR = "#FF7479"


def blend_color(start: str, end: str, amount: float) -> str:
    """Return the RGB interpolation between two #RRGGBB colors."""

    amount = max(0.0, min(1.0, amount))
    start_rgb = tuple(int(start[index : index + 2], 16) for index in (1, 3, 5))
    end_rgb = tuple(int(end[index : index + 2], 16) for index in (1, 3, 5))
    mixed = tuple(round(a + (b - a) * amount) for a, b in zip(start_rgb, end_rgb))
    return "#" + "".join(f"{channel:02X}" for channel in mixed)


def rounded_rectangle_points(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
) -> tuple[float, ...]:
    """Build a smooth polygon path for a rounded rectangle."""

    radius = max(0.0, min(radius, abs(x2 - x1) / 2, abs(y2 - y1) / 2))
    points: list[float] = []
    for center_x, center_y, start_angle in (
        (x2 - radius, y1 + radius, -90),
        (x2 - radius, y2 - radius, 0),
        (x1 + radius, y2 - radius, 90),
        (x1 + radius, y1 + radius, 180),
    ):
        for step in range(6):
            angle = math.radians(start_angle + step * 18)
            points.extend(
                (center_x + radius * math.cos(angle), center_y + radius * math.sin(angle))
            )
    return tuple(points)


class CaptureCard(tk.Canvas):
    """Keyboard-accessible source card with hover and selected states."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        label: str,
        detail: str,
        icon: str,
        command: Callable[[], None],
        width: int = 238,
        height: int = 122,
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=BACKGROUND,
            highlightthickness=0,
            bd=0,
            takefocus=True,
            cursor="hand2",
        )
        self.label = label
        self.detail = detail
        self.icon = icon
        self.command = command
        self.selected = False
        self.enabled = True
        self.hovered = False
        self.focused = False
        self.bind("<Button-1>", lambda _event: self.invoke())
        self.bind("<Return>", lambda _event: self.invoke())
        self.bind("<space>", lambda _event: self.invoke())
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", self._focus_out)
        self._draw()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def invoke(self) -> None:
        if self.enabled:
            self.focus_set()
            self.command()

    def _enter(self, _event: object) -> None:
        self.hovered = True
        self._draw()

    def _leave(self, _event: object) -> None:
        self.hovered = False
        self._draw()

    def _focus_in(self, _event: object) -> None:
        self.focused = True
        self._draw()

    def _focus_out(self, _event: object) -> None:
        self.focused = False
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        width = int(self.cget("width"))
        height = int(self.cget("height"))
        fill = SURFACE_HOVER if self.hovered and self.enabled else SURFACE
        if not self.enabled:
            fill = blend_color(BACKGROUND, SURFACE, 0.56)
        outline = BORDER
        outline_width = 1
        if self.selected:
            outline = blend_color(CORAL, VIOLET, 0.45)
            outline_width = 3
            self.create_polygon(
                rounded_rectangle_points(2, 2, width - 2, height - 2, 17),
                fill=blend_color(SURFACE, VIOLET, 0.08),
                outline="",
                smooth=True,
            )
        elif self.focused:
            outline = VIOLET
            outline_width = 2
        self.create_polygon(
            rounded_rectangle_points(4, 4, width - 4, height - 4, 15),
            fill=fill,
            outline=outline,
            width=outline_width,
            smooth=True,
            splinesteps=24,
        )
        icon_color = CORAL if self.selected else (MUTED if self.enabled else SUBTLE)
        self._draw_icon(width / 2, 36, icon_color)
        text_color = TEXT if self.enabled else SUBTLE
        self.create_text(
            width / 2,
            75,
            text=self.label,
            fill=text_color,
            font=("Segoe UI Semibold", 11),
        )
        self.create_text(
            width / 2,
            98,
            text=self.detail,
            fill=MUTED if self.enabled else SUBTLE,
            font=("Segoe UI", 8),
        )
        if self.selected:
            self.create_oval(width - 31, 13, width - 13, 31, fill=CORAL, outline="")
            self.create_line(
                width - 27,
                22,
                width - 23,
                26,
                width - 17,
                18,
                fill=TEXT,
                width=2,
                capstyle="round",
                joinstyle="round",
            )

    def _draw_icon(self, center_x: float, center_y: float, color: str) -> None:
        if self.icon in {"monitor", "screen"}:
            self.create_rectangle(
                center_x - 22,
                center_y - 15,
                center_x + 22,
                center_y + 12,
                outline=color,
                width=2,
            )
            self.create_line(center_x, center_y + 12, center_x, center_y + 18, fill=color, width=2)
            self.create_line(center_x - 11, center_y + 18, center_x + 11, center_y + 18, fill=color, width=2)
            if self.icon == "screen":
                self.create_line(center_x - 14, center_y - 8, center_x + 14, center_y - 8, fill=color)
        else:
            self.create_rectangle(
                center_x - 23,
                center_y - 16,
                center_x + 23,
                center_y + 14,
                outline=color,
                width=2,
            )
            self.create_line(center_x - 23, center_y - 8, center_x + 23, center_y - 8, fill=color)
            for offset in (-16, -10, -4):
                self.create_oval(
                    center_x + offset - 1,
                    center_y - 13,
                    center_x + offset + 1,
                    center_y - 11,
                    fill=color,
                    outline="",
                )


class ToggleSwitch(tk.Canvas):
    """A small animated switch backed by a BooleanVar."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        variable: tk.BooleanVar,
        command: Callable[[], None],
    ) -> None:
        super().__init__(
            parent,
            width=52,
            height=30,
            bg=SURFACE,
            highlightthickness=0,
            bd=0,
            takefocus=True,
            cursor="hand2",
        )
        self.variable = variable
        self.command = command
        self.enabled = True
        self._knob_position = 1.0 if variable.get() else 0.0
        self._animation_job: str | None = None
        self.bind("<Button-1>", lambda _event: self.invoke())
        self.bind("<Return>", lambda _event: self.invoke())
        self.bind("<space>", lambda _event: self.invoke())
        self.bind("<Destroy>", self._on_destroy)
        self._draw()

    def invoke(self) -> None:
        if not self.enabled:
            return
        self.variable.set(not self.variable.get())
        self.command()
        self._animate()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def _animate(self) -> None:
        target = 1.0 if self.variable.get() else 0.0
        distance = target - self._knob_position
        if abs(distance) < 0.02:
            self._knob_position = target
            self._animation_job = None
            self._draw()
            return
        self._knob_position += distance * 0.32
        self._draw()
        self._animation_job = self.after(16, self._animate)

    def _draw(self) -> None:
        self.delete("all")
        active = self.variable.get()
        track = CORAL if active else BORDER
        if not self.enabled:
            track = blend_color(BACKGROUND, track, 0.45)
        self.create_polygon(
            rounded_rectangle_points(2, 3, 50, 27, 12),
            fill=track,
            outline="",
            smooth=True,
        )
        knob_x = 15 + (22 * self._knob_position)
        knob = TEXT if self.enabled else SUBTLE
        self.create_oval(knob_x - 9, 6, knob_x + 9, 24, fill=knob, outline="")

    def _on_destroy(self, event: tk.Event[tk.Misc]) -> None:
        if event.widget is self and self._animation_job is not None:
            try:
                self.after_cancel(self._animation_job)
            except tk.TclError:
                pass
            self._animation_job = None


class AnimatedActionButton(tk.Canvas):
    """Primary action with a restrained breathing border and clear state API."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        text: str,
        command: Callable[[], None],
        width: int = 780,
        height: int = 62,
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=BACKGROUND,
            highlightthickness=0,
            bd=0,
            takefocus=True,
            cursor="hand2",
        )
        self.text = text
        self.command = command
        self.variant = "primary"
        self.state = "normal"
        self.hovered = False
        self.focused = False
        self._pressed = False
        self._started_at = time.monotonic()
        self.animation_job: str | None = None
        self.bind("<Button-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Return>", lambda _event: self.invoke())
        self.bind("<space>", lambda _event: self.invoke())
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", self._focus_out)
        self.bind("<Destroy>", self._on_destroy)
        self._animate()

    def set(
        self,
        *,
        text: str | None = None,
        variant: str | None = None,
        state: str | None = None,
    ) -> None:
        if text is not None:
            self.text = text
        if variant is not None:
            self.variant = variant
        if state is not None:
            self.state = state
            self.configure(cursor="hand2" if state == "normal" else "arrow")
        self._draw()

    def invoke(self) -> None:
        if self.state == "normal":
            self.focus_set()
            self.command()

    def _press(self, _event: object) -> None:
        if self.state == "normal":
            self._pressed = True
            self._draw()

    def _release(self, _event: object) -> None:
        if self._pressed:
            self._pressed = False
            self._draw()
            self.invoke()

    def _enter(self, _event: object) -> None:
        self.hovered = True
        self._draw()

    def _leave(self, _event: object) -> None:
        self.hovered = False
        self._pressed = False
        self._draw()

    def _focus_in(self, _event: object) -> None:
        self.focused = True
        self._draw()

    def _focus_out(self, _event: object) -> None:
        self.focused = False
        self._draw()

    def _animate(self) -> None:
        self._draw()
        self.animation_job = self.after(40, self._animate)

    def _draw(self) -> None:
        self.delete("all")
        width = int(self.cget("width"))
        height = int(self.cget("height"))
        elapsed = time.monotonic() - self._started_at
        pulse = (math.sin(elapsed * 2.2) + 1) / 2
        primary = CORAL if self.variant != "danger" else blend_color(CORAL, "#E2353D", 0.45)
        if self.hovered and self.state == "normal":
            primary = blend_color(primary, "#FFFFFF", 0.08)
        if self._pressed:
            primary = blend_color(primary, BACKGROUND, 0.16)
        if self.state != "normal":
            primary = blend_color(SURFACE, SUBTLE, 0.32)
        glow = blend_color(BACKGROUND, VIOLET, 0.12 + pulse * 0.08)
        self.create_polygon(
            rounded_rectangle_points(1, 1, width - 1, height - 1, 17),
            fill=glow,
            outline="",
            smooth=True,
        )
        outline = TEXT if self.focused else blend_color(CORAL, VIOLET, 0.30 + pulse * 0.25)
        self.create_polygon(
            rounded_rectangle_points(4, 4, width - 4, height - 4, 15),
            fill=primary,
            outline=outline,
            width=2 if self.focused else 1,
            smooth=True,
        )
        center_x = width / 2
        self.create_oval(center_x - 102, height / 2 - 10, center_x - 82, height / 2 + 10, outline=TEXT, width=2)
        self.create_oval(center_x - 96, height / 2 - 4, center_x - 88, height / 2 + 4, fill=TEXT, outline="")
        self.create_text(
            center_x + 16,
            height / 2,
            text=self.text,
            fill=TEXT if self.state == "normal" else MUTED,
            font=("Segoe UI Semibold", 13),
        )

    def _on_destroy(self, event: tk.Event[tk.Misc]) -> None:
        if event.widget is self and self.animation_job is not None:
            try:
                self.after_cancel(self.animation_job)
            except tk.TclError:
                pass
            self.animation_job = None


class OrbitalRecorder(tk.Canvas):
    """Animated visual anchor that communicates recorder state."""

    STATE_COLORS = {
        "ready": CORAL,
        "busy": VIOLET,
        "recording": CORAL,
        "saved": GREEN,
        "error": ERROR,
    }

    def __init__(
        self,
        parent: tk.Misc,
        *,
        width: int = 520,
        height: int = 190,
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=BACKGROUND,
            highlightthickness=0,
            bd=0,
        )
        self.state = "ready"
        self._started_at = time.monotonic()
        self.animation_job: str | None = None
        self.bind("<Destroy>", self._on_destroy)
        self._animate()

    def set_state(self, state: str) -> None:
        if state not in self.STATE_COLORS:
            raise ValueError(f"unknown orbital state: {state}")
        self.state = state
        self._draw()

    def _animate(self) -> None:
        self._draw()
        self.animation_job = self.after(33, self._animate)

    def _draw(self) -> None:
        self.delete("all")
        width = int(self.cget("width"))
        height = int(self.cget("height"))
        center_x = width / 2
        center_y = height / 2
        elapsed = time.monotonic() - self._started_at
        state_color = self.STATE_COLORS[self.state]
        pulse_speed = 4.2 if self.state == "recording" else 1.8
        pulse = (math.sin(elapsed * pulse_speed) + 1) / 2

        for radius, amount in ((52, 0.08), (45, 0.14), (38, 0.24)):
            self.create_oval(
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
                fill=blend_color(BACKGROUND, state_color, amount + pulse * 0.05),
                outline="",
            )

        orbit_a = self._ellipse_points(center_x, center_y, 210, 49, -0.16)
        orbit_b = self._ellipse_points(center_x, center_y, 178, 68, 0.18)
        self.create_line(*orbit_a, fill=blend_color(BACKGROUND, CORAL, 0.58), width=2, smooth=True)
        self.create_line(*orbit_b, fill=blend_color(BACKGROUND, VIOLET, 0.56), width=2, smooth=True)

        for angle, radius_x, radius_y, rotation, color in (
            (elapsed * 0.8, 210, 49, -0.16, CORAL),
            (-elapsed * 0.55 + 2.2, 178, 68, 0.18, VIOLET),
        ):
            dot_x, dot_y = self._ellipse_position(
                center_x, center_y, radius_x, radius_y, rotation, angle
            )
            self.create_oval(dot_x - 5, dot_y - 5, dot_x + 5, dot_y + 5, fill=color, outline="")

        ring_color = blend_color(state_color, TEXT, 0.15)
        self.create_oval(
            center_x - 47,
            center_y - 47,
            center_x + 47,
            center_y + 47,
            outline=ring_color,
            width=3,
        )
        dot_radius = 17 + pulse * (3 if self.state == "recording" else 1.5)
        self.create_oval(
            center_x - dot_radius,
            center_y - dot_radius,
            center_x + dot_radius,
            center_y + dot_radius,
            fill=state_color,
            outline=blend_color(state_color, TEXT, 0.28),
            width=1,
        )

    @staticmethod
    def _ellipse_position(
        center_x: float,
        center_y: float,
        radius_x: float,
        radius_y: float,
        rotation: float,
        angle: float,
    ) -> tuple[float, float]:
        x = radius_x * math.cos(angle)
        y = radius_y * math.sin(angle)
        return (
            center_x + x * math.cos(rotation) - y * math.sin(rotation),
            center_y + x * math.sin(rotation) + y * math.cos(rotation),
        )

    @classmethod
    def _ellipse_points(
        cls,
        center_x: float,
        center_y: float,
        radius_x: float,
        radius_y: float,
        rotation: float,
    ) -> tuple[float, ...]:
        points: list[float] = []
        for step in range(65):
            angle = (math.tau * step) / 64
            points.extend(
                cls._ellipse_position(
                    center_x,
                    center_y,
                    radius_x,
                    radius_y,
                    rotation,
                    angle,
                )
            )
        return tuple(points)

    def _on_destroy(self, event: tk.Event[tk.Misc]) -> None:
        if event.widget is self and self.animation_job is not None:
            try:
                self.after_cancel(self.animation_job)
            except tk.TclError:
                pass
            self.animation_job = None
