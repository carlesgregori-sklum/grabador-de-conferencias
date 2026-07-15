from __future__ import annotations

import tkinter as tk
import unittest

from bizneo_recorder.ui import (
    AnimatedActionButton,
    CaptureCard,
    OrbitalRecorder,
    ToggleSwitch,
    WaveformIndicator,
    blend_color,
    render_supersampled,
    rounded_rectangle_points,
)


class UiDrawingTests(unittest.TestCase):
    def test_blend_color_interpolates_and_clamps(self) -> None:
        self.assertEqual(blend_color("#000000", "#FFFFFF", 0.5), "#808080")
        self.assertEqual(blend_color("#112233", "#FFFFFF", -1), "#112233")
        self.assertEqual(blend_color("#000000", "#ABCDEF", 2), "#ABCDEF")

    def test_rounded_rectangle_points_stay_inside_bounds(self) -> None:
        points = rounded_rectangle_points(0, 0, 100, 50, 12)

        self.assertGreater(len(points), 16)
        self.assertGreaterEqual(min(points[0::2]), 0)
        self.assertLessEqual(max(points[0::2]), 100)
        self.assertGreaterEqual(min(points[1::2]), 0)
        self.assertLessEqual(max(points[1::2]), 50)

    def test_supersampled_render_blends_curved_edges(self) -> None:
        image = render_supersampled(
            18,
            18,
            "#000000",
            lambda drawing: drawing.ellipse((3, 3, 15, 15), fill="#FFFFFF"),
            scale=4,
        )

        self.assertEqual(image.size, (18, 18))
        channels = {
            image.getpixel((x, y))[0]
            for y in range(image.height)
            for x in range(image.width)
        }
        self.assertIn(0, channels)
        self.assertIn(255, channels)
        self.assertTrue(any(0 < channel < 255 for channel in channels))


class UiWidgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self) -> None:
        self.root.destroy()

    def test_capture_card_exposes_selection_and_activation(self) -> None:
        activations: list[str] = []
        card = CaptureCard(
            self.root,
            label="Pestaña de Chrome",
            detail="Audio de la pestaña",
            icon="tab",
            command=lambda: activations.append("tab"),
        )

        card.set_selected(True)
        card.invoke()

        self.assertTrue(card.selected)
        self.assertEqual(activations, ["tab"])
        self.assertEqual(card.cget("takefocus"), "1")

    def test_disabled_capture_card_does_not_activate(self) -> None:
        activations: list[bool] = []
        card = CaptureCard(
            self.root,
            label="Pantalla completa",
            detail="Sin selector",
            icon="monitor",
            command=lambda: activations.append(True),
        )

        card.set_enabled(False)
        card.invoke()

        self.assertEqual(activations, [])

    def test_toggle_switch_updates_variable_and_runs_command(self) -> None:
        variable = tk.BooleanVar(value=False)
        values: list[bool] = []
        toggle = ToggleSwitch(
            self.root,
            variable=variable,
            command=lambda: values.append(variable.get()),
        )

        toggle.invoke()

        self.assertTrue(variable.get())
        self.assertEqual(values, [True])

    def test_action_button_tracks_text_variant_and_disabled_state(self) -> None:
        activations: list[bool] = []
        button = AnimatedActionButton(
            self.root,
            text="Iniciar grabación",
            command=lambda: activations.append(True),
        )

        button.set(text="Finalizar y guardar", variant="danger", state="disabled")
        button.invoke()

        self.assertEqual(button.text, "Finalizar y guardar")
        self.assertEqual(button.variant, "danger")
        self.assertEqual(button.state, "disabled")
        self.assertEqual(activations, [])

        button.set(state="normal")
        button.invoke()
        self.assertEqual(activations, [True])

    def test_orbital_recorder_changes_state_without_restarting_loop(self) -> None:
        orb = OrbitalRecorder(self.root)
        animation_job = orb.animation_job

        orb.set_state("recording")

        self.assertEqual(orb.state, "recording")
        self.assertIsNotNone(animation_job)
        self.assertEqual(orb.animation_job, animation_job)

    def test_waveform_indicator_can_be_activated_and_paused(self) -> None:
        waveform = WaveformIndicator(self.root)

        waveform.set_active(True)

        self.assertTrue(waveform.active)
        self.assertIsNotNone(waveform.animation_job)

        waveform.set_active(False)
        self.assertFalse(waveform.active)


if __name__ == "__main__":
    unittest.main()
