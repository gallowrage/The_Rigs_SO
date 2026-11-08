from __future__ import annotations

import ctypes
from unittest.mock import MagicMock

from src import casio_midi_hook
from src.casio_midi_hook import MIM_DATA, CasioMidiHook


def test_midi_callback_queues_mim_data() -> None:
    hook = CasioMidiHook()
    hook._midi_callback(None, MIM_DATA, 0, 0x00403C90, 12345)
    assert not hook.event_queue.empty()
    assert hook.event_queue.get_nowait() == (0x00403C90, 12345)

    hook._midi_callback(None, 0x999, 0, 0x00403C90, 12345)
    assert hook.event_queue.empty()


def test_worker_loop_parses_note_on_off_and_status(capsys) -> None:
    hook = CasioMidiHook()
    # Note On (status=0x90, note=60, velocity=64)
    hook.event_queue.put((0x00403C90, 100))
    # Note Off via 0x80 (status=0x80, note=60, velocity=0)
    hook.event_queue.put((0x00003C80, 200))
    # Custom status (0xB0 CC)
    hook.event_queue.put((0x007F07B0, 300))

    class StopAfterDrain:
        def __init__(self, q):
            self.q = q
            self.calls = 0

        def __bool__(self):
            self.calls += 1
            return self.calls <= 4

    hook.running = StopAfterDrain(hook.event_queue)
    hook._worker_loop()

    out = capsys.readouterr().out
    assert "NOTE ON  | Note: 60  | Velocity: 64" in out
    assert "NOTE OFF | Note: 60  | Velocity: 0" in out
    assert "STATUS 0xb0" in out


def test_start_and_stop_lifecycle(monkeypatch) -> None:
    fake_winmm = MagicMock()
    fake_winmm.midiInOpen.return_value = 0
    monkeypatch.setattr(casio_midi_hook, "winmm", fake_winmm)

    hook = CasioMidiHook()
    hook.hMidiIn = casio_midi_hook.wintypes.HANDLE(1)
    assert hook.start(0) is True
    assert hook.running is True
    fake_winmm.midiInStart.assert_called_once()

    hook.stop()
    assert hook.running is False
    assert hook.hMidiIn is None
    fake_winmm.midiInStop.assert_called_once()
    fake_winmm.midiInReset.assert_called_once()
    fake_winmm.midiInClose.assert_called_once()


def test_start_returns_false_on_winmm_error(monkeypatch) -> None:
    fake_winmm = MagicMock()
    fake_winmm.midiInOpen.return_value = 4
    monkeypatch.setattr(casio_midi_hook, "winmm", fake_winmm)

    hook = CasioMidiHook()
    assert hook.start(1) is False
    assert hook.running is False


def test_list_and_monitor_no_devices(monkeypatch, capsys) -> None:
    fake_winmm = MagicMock()
    fake_winmm.midiInGetNumDevs.return_value = 0
    monkeypatch.setattr(casio_midi_hook, "winmm", fake_winmm)

    casio_midi_hook.list_and_monitor()
    out = capsys.readouterr().out
    assert "No active MIDI INPUT ports" in out


def test_list_and_monitor_with_device(monkeypatch, capsys) -> None:
    fake_winmm = MagicMock()
    fake_winmm.midiInGetNumDevs.return_value = 1

    def fake_get_caps(idx, caps_ptr, size):
        caps = ctypes.cast(caps_ptr, ctypes.POINTER(casio_midi_hook.MIDIINCAPSW)).contents
        caps.szPname = "Casio USB-MIDI"
        return 0

    fake_winmm.midiInGetDevCapsW.side_effect = fake_get_caps
    monkeypatch.setattr(casio_midi_hook, "winmm", fake_winmm)

    class DummyHook:
        is_active = False

        def start(self, dev_id: int) -> bool:
            return True

        def stop(self) -> None:
            pass

    monkeypatch.setattr(casio_midi_hook, "CasioMidiHook", DummyHook)
    monkeypatch.setattr(casio_midi_hook.time, "sleep", lambda _: None)

    casio_midi_hook.list_and_monitor()
    out = capsys.readouterr().out
    assert "Casio USB-MIDI" in out
    assert "MIDI Hook cleanly detached" in out
