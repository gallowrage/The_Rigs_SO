import customtkinter as ctk
import tkinter as tk
from typing import Dict, Any

class MaestroUI(ctk.CTkFrame):
    """
    Frontend CustomTkinter UI for Ryboto Maestro (v1.3)
    Implements the structural and functional breakdown requested.
    """
    
    def __init__(self, master, controller, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        
        # Configure grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  # Left Sidebar (Telemetry)
        self.grid_columnconfigure(1, weight=3)  # Main View (3D Anchor / Radial)
        self.grid_columnconfigure(2, weight=1)  # Right Sidebar (Loop/Stem Editor)

        self._build_telemetry_panel()
        self._build_main_performance_view()
        self._build_loop_editor_panel()
        
        # Subscribe to controller state
        self.controller.register_state_callback(self.update_ui_state)

    def _build_telemetry_panel(self):
        """Left Sidebar: Live Telemetry & Twitch Settings"""
        self.left_frame = ctk.CTkFrame(self, corner_radius=0)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(self.left_frame, text="Live Telemetry", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        self.chord_label = ctk.CTkLabel(self.left_frame, text="Current Chord: C", font=ctk.CTkFont(size=24))
        self.chord_label.pack(pady=20)
        
        self.style_label = ctk.CTkLabel(self.left_frame, text="Style: Synth Craze")
        self.style_label.pack(pady=5)
        
        self.tempo_label = ctk.CTkLabel(self.left_frame, text="Tempo: 120 BPM")
        self.tempo_label.pack(pady=5)
        
        # Twitch Integration
        ctk.CTkLabel(self.left_frame, text="Twitch Setup", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(30, 10))
        self.twitch_channel = ctk.CTkEntry(self.left_frame, placeholder_text="Twitch Channel")
        self.twitch_channel.pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(self.left_frame, text="Connect", command=self._on_twitch_connect).pack(pady=5)

    def _build_main_performance_view(self):
        """Center View: 3D Anchor placeholder and Action Buttons (Radial Menu alternative)"""
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Placeholder for 3D Robotic DJ / WebGL View
        self.maestro_canvas = ctk.CTkCanvas(self.center_frame, bg="black", highlightthickness=0)
        self.maestro_canvas.pack(expand=True, fill="both", padx=20, pady=20)
        self.maestro_canvas.create_text(200, 200, text="3D Maestro Anchor (Gold/Red)", fill="white", font=("Arial", 16))
        
        # Action Buttons (Pacing & Effects)
        btn_frame = ctk.CTkFrame(self.center_frame)
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(btn_frame, text="Slower!", command=lambda: self.controller.trigger_action("speed_adjust", direction="slower")).pack(side="left", padx=5, expand=True)
        ctk.CTkButton(btn_frame, text="Revert Speed", command=lambda: self.controller.trigger_action("speed_adjust", direction="revert")).pack(side="left", padx=5, expand=True)
        ctk.CTkButton(btn_frame, text="Faster!", command=lambda: self.controller.trigger_action("speed_adjust", direction="faster")).pack(side="left", padx=5, expand=True)
        
        style_frame = ctk.CTkFrame(self.center_frame)
        style_frame.pack(fill="x", padx=20, pady=5)
        for style in ["Chiptune", "Piano Mania", "Synth Craze", "Misty Wall"]:
            ctk.CTkButton(style_frame, text=style, command=lambda s=style: self.controller.trigger_action("change_style", style=s)).pack(side="left", padx=5, expand=True)

    def _build_loop_editor_panel(self):
        """Right Sidebar: Loop & Stem Editor"""
        self.right_frame = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.right_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(self.right_frame, text="Stem Layers", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        self.sliders = {}
        stems = ["Drums", "Bass", "Long Chords", "Drone & Melody"]
        
        for stem in stems:
            frame = ctk.CTkFrame(self.right_frame)
            frame.pack(fill="x", pady=10, padx=10)
            ctk.CTkLabel(frame, text=stem, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=2)
            
            # Volume slider
            ctk.CTkLabel(frame, text="Volume").pack(anchor="w", padx=5)
            slider = ctk.CTkSlider(frame, from_=0, to=1, command=lambda val, s=stem: self._on_stem_vol_change(s, val))
            slider.pack(fill="x", padx=5, pady=5)
            self.sliders[f"{stem}_vol"] = slider

    def _on_twitch_connect(self):
        chan = self.twitch_channel.get()
        self.controller.configure_twitch(channel=chan, username="", token="")
        # In a real app, you would schedule the async task here

    def _on_stem_vol_change(self, stem: str, value: float):
        stem_key = stem.lower().replace(" ", "_").replace("&_", "")
        self.controller.update_stem(stem_key, volume=value)

    def update_ui_state(self, state: Dict[str, Any]):
        """Update UI components when backend state changes."""
        self.chord_label.configure(text=f"Current Chord: {state['chords']['current']}")
        self.tempo_label.configure(text=f"Tempo: {state['tempo']} BPM")
        self.style_label.configure(text=f"Style: {state['style']}")
        # Additional slider syncs can go here

if __name__ == "__main__":
    # Test Runner
    from maestro_controller import RybotoMaestroController
    
    app = ctk.CTk()
    app.title("Ryboto Maestro (v1.3)")
    app.geometry("1200x800")
    
    controller = RybotoMaestroController()
    ui = MaestroUI(app, controller)
    ui.pack(expand=True, fill="both")
    
    app.mainloop()
