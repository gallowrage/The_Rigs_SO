from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from src.ryboto_maestro.maestro_controller import RybotoMaestroController


def test_controller_initial_state() -> None:
    ctrl = RybotoMaestroController()
    assert ctrl.state["chords"]["current"] == "C"
    assert ctrl.state["tempo"] == 120
    assert ctrl.state["style"] == "Synth Craze"
    assert ctrl.state["twitch"]["connected"] is False


def test_controller_callbacks_and_exception_handling() -> None:
    ctrl = RybotoMaestroController()
    observed = []

    def bad_callback(_state):
        raise RuntimeError("Callback failure")

    ctrl.register_state_callback(bad_callback)
    ctrl.register_state_callback(lambda s: observed.append(s["tempo"]))

    ctrl.trigger_action("speed_adjust", direction="faster")
    assert observed == [130]
    assert ctrl.state["tempo"] == 130


def test_controller_trigger_actions() -> None:
    ctrl = RybotoMaestroController()
    ctrl.trigger_action("speed_adjust", direction="faster")
    assert ctrl.state["tempo"] == 130

    ctrl.trigger_action("speed_adjust", direction="slower")
    assert ctrl.state["tempo"] == 120

    ctrl.trigger_action("speed_adjust", direction="faster")
    ctrl.trigger_action("speed_adjust", direction="revert")
    assert ctrl.state["tempo"] == 120

    ctrl.trigger_action("change_style", style="Chiptune")
    assert ctrl.state["style"] == "Chiptune"


def test_controller_twitch_and_jamming_settings() -> None:
    ctrl = RybotoMaestroController()
    ctrl.configure_twitch("gallowrage_ch", "bot_user", "oauth:token_placeholder")
    assert ctrl.state["twitch"]["channel"] == "gallowrage_ch"
    assert ctrl.state["twitch"]["username"] == "bot_user"

    asyncio.run(ctrl.connect_twitch())
    assert ctrl.state["twitch"]["connected"] is True

    ctrl.update_jamming_settings(green_screen=True, time_limit_sec=600, unknown_key=123)
    assert ctrl.state["jamming"]["green_screen"] is True
    assert ctrl.state["jamming"]["time_limit_sec"] == 600
    assert "unknown_key" not in ctrl.state["jamming"]


def test_controller_stem_and_midi_input() -> None:
    ctrl = RybotoMaestroController()
    ctrl.update_stem("drums", volume=0.95, solo=True)
    assert ctrl.state["stems"]["drums"]["volume"] == 0.95
    assert ctrl.state["stems"]["drums"]["solo"] is True

    ctrl.update_stem("nonexistent_stem", volume=0.1)
    assert "nonexistent_stem" not in ctrl.state["stems"]

    ctrl.process_midi_input("chord_change", {"chord": "Am7"})
    assert ctrl.state["chords"]["current"] == "Am7"

    ctrl.process_midi_input("other_event", {"chord": "G"})
    assert ctrl.state["chords"]["current"] == "Am7"


def test_maestro_ui_methods_with_mocked_widgets(monkeypatch) -> None:
    from src.ryboto_maestro import maestro_ui

    ctrl = RybotoMaestroController()
    ui = maestro_ui.MaestroUI.__new__(maestro_ui.MaestroUI)
    ui.controller = ctrl
    ui.twitch_channel = MagicMock()
    ui.twitch_channel.get.return_value = "nexus_live"
    ui.chord_label = MagicMock()
    ui.tempo_label = MagicMock()
    ui.style_label = MagicMock()

    ui._on_twitch_connect()
    assert ctrl.state["twitch"]["channel"] == "nexus_live"

    ui._on_stem_vol_change("Drone & Melody", 0.42)
    assert ctrl.state["stems"]["drone_melody"]["volume"] == 0.42

    ui.update_ui_state(ctrl.state)
    ui.chord_label.configure.assert_called_with(text="Current Chord: C")
    ui.tempo_label.configure.assert_called_with(text="Tempo: 120 BPM")
    ui.style_label.configure.assert_called_with(text="Style: Synth Craze")
