"""
Casio 61-Key MIDI Monitor / Hook Diagnostic (Omega-VANE Optimized)
Uses ctypes to access Windows Multimedia (winmm.dll) for low-latency MIDI input.
"""

import time
import sys
import ctypes
from ctypes import wintypes
import queue
import threading

# WinMM API Definitions
winmm = ctypes.windll.winmm
DWORD_PTR = ctypes.c_void_p

MidiInProc = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.UINT,
    DWORD_PTR,
    DWORD_PTR,
    DWORD_PTR
)

MIM_DATA = 0x3C3
CALLBACK_FUNCTION = 0x30000

class MIDIINCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("vDriverVersion", wintypes.DWORD),
        ("szPname", wintypes.WCHAR * 32),
        ("dwSupport", wintypes.DWORD),
    ]

class CasioMidiHook:
    def __init__(self):
        self.hMidiIn = wintypes.HANDLE()
        self.event_queue = queue.Queue()
        self.running = False
        self.worker_thread = None
        # Keep a reference to the callback to prevent garbage collection
        self._callback = MidiInProc(self._midi_callback)

    def _midi_callback(self, hMidiIn, wMsg, dwInstance, dwParam1, dwParam2):
        if wMsg == MIM_DATA:
            # Lightweight callback: queue raw event
            # dwParam1 contains status, note, and velocity
            # dwParam2 contains the timestamp
            self.event_queue.put((dwParam1, dwParam2))

    def _worker_loop(self):
        while self.running:
            try:
                dwParam1, timestamp = self.event_queue.get(timeout=0.1)
                status = dwParam1 & 0xFF
                note = (dwParam1 >> 8) & 0xFF
                velocity = (dwParam1 >> 16) & 0xFF
                
                if (status & 0xF0) == 0x90 and velocity > 0:
                    event_type = "NOTE ON "
                elif (status & 0xF0) == 0x80 or ((status & 0xF0) == 0x90 and velocity == 0):
                    event_type = "NOTE OFF"
                else:
                    event_type = f"STATUS {hex(status)}"
                    
                print(f"[{timestamp}] {event_type} | Note: {note:<3} | Velocity: {velocity:<3} | Raw: {hex(dwParam1)}", flush=True)
                self.event_queue.task_done()
            except queue.Empty:
                continue

    def start(self, device_id: int):
        res = winmm.midiInOpen(ctypes.byref(self.hMidiIn), device_id, self._callback, 0, CALLBACK_FUNCTION)
        if res != 0:
            print(f"[!] Failed to open MIDI device. Error code: {res}")
            return False
            
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        winmm.midiInStart(self.hMidiIn)
        return True

    def stop(self):
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)
            
        if self.hMidiIn:
            winmm.midiInStop(self.hMidiIn)
            winmm.midiInReset(self.hMidiIn)
            winmm.midiInClose(self.hMidiIn)
            self.hMidiIn = None

def list_and_monitor():
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
        
    num_devs = winmm.midiInGetNumDevs()
    print("=" * 60)
    print(f"OMEGA-VANE MIDI DIAGNOSTIC (Total Ports Found: {num_devs})")
    print("=" * 60)
    
    input_devices = []
    for i in range(num_devs):
        caps = MIDIINCAPSW()
        res = winmm.midiInGetDevCapsW(i, ctypes.byref(caps), ctypes.sizeof(caps))
        if res == 0:
            name = caps.szPname
            print(f"[{i:02d}] {name:<35} | Type: INPUT | Backend: winmm (native)")
            input_devices.append((i, name))
            
    print("=" * 60)
    if not input_devices:
        print("[!] No active MIDI INPUT ports currently visible to MMSystem.")
        print("[*] Troubleshooting steps for 61-key Casio:")
        print("    1. Verify USB-MIDI cable is firmly connected to PC and keyboard.")
        print("    2. Ensure Casio power is ON.")
        print("    3. If using standard 5-pin DIN to USB adapter, verify IN/OUT cables are crossed.")
        return

    device_id, dev_name = input_devices[0]
    print(f"[*] Attaching native WinMM MIDI listener to Device [{device_id}]: {dev_name}")
    
    hook = CasioMidiHook()
    if hook.start(device_id):
        print("[*] Listener active. Press keys on your 61-key Casio (Press Ctrl+C to stop)...")
        try:
            while True:
                time.sleep(0.1)
                if not getattr(hook, "is_active", True):
                    break
        except KeyboardInterrupt:
            print("\n[*] MIDI Monitor stopped by user.")
        finally:
            hook.stop()
            print("[*] MIDI Hook cleanly detached. Handles released.")

if __name__ == "__main__":
    list_and_monitor()
