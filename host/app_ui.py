import tkinter as tk
from tkinter import ttk
import threading

# Import core modules (assuming they exist in the same directory)
try:
    from transports import SerialTransport
    from lighting_engine import LightingEngine
    from screen_analyzer import ScreenAnalyzer
    from audio_analyzer import AudioAnalyzer
    from music_analyzer import MusicAnalyzer
    from dev_events import DevEventHandler
    from app_state import AppState, AppMode
    import diagnostics as diag
except ImportError:
    pass

class DevLightsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DEVLIGHTS")
        self.root.geometry("400x550")
        
        # System setup
        self.app_state = AppState()
        self.transport = SerialTransport()
        self.engine = LightingEngine(self.transport, self.app_state)
        
        self.screen_analyzer = ScreenAnalyzer(self.engine)
        self.audio_analyzer = AudioAnalyzer(self.engine)
        self.music_analyzer = MusicAnalyzer(self.engine)
        self.dev_events = DevEventHandler(self.engine)
        
        # Start background services
        self.transport.connect()
        self.dev_events.start()
        
        self.build_ui()
        self.apply_mode(self.app_state.mode)
        
        # Start diagnostic update loop
        self.update_diagnostics()

    def build_ui(self):
        # Status
        self.status_var = tk.StringVar()
        tk.Label(self.root, textvariable=self.status_var, font=("Helvetica", 14, "bold")).pack(pady=10)
        
        # Mode Selection
        tk.Label(self.root, text="Mode").pack(anchor="w", padx=20)
        self.mode_var = tk.StringVar(value=self.app_state.mode.capitalize())
        modes = [AppMode.MOVIE, AppMode.MUSIC, AppMode.DEVELOPER, AppMode.GAME, AppMode.CUSTOM]
        mode_cb = ttk.Combobox(self.root, textvariable=self.mode_var, values=[m.capitalize() for m in modes], state="readonly")
        mode_cb.pack(fill="x", padx=20, pady=5)
        mode_cb.bind("<<ComboboxSelected>>", self.on_mode_change)
        
        # Brightness Limit
        tk.Label(self.root, text="Max Brightness").pack(anchor="w", padx=20, pady=(10,0))
        self.brightness_var = tk.DoubleVar(value=self.app_state.get_current_settings().get("brightness_limit", 1.0) * 100)
        brightness_slider = tk.Scale(self.root, from_=0, to=100, orient="horizontal", variable=self.brightness_var, command=self.on_brightness_change)
        brightness_slider.pack(fill="x", padx=20)
        
        # Test Colors
        tk.Label(self.root, text="Test Colors (Overrides active mode)").pack(anchor="w", padx=20, pady=(20, 5))
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill="x", padx=20)
        
        tk.Button(btn_frame, text="Red", bg="red", fg="black", command=lambda: self.engine.set_ambient_color(255, 0, 0)).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_frame, text="Green", bg="green", fg="black", command=lambda: self.engine.set_ambient_color(0, 255, 0)).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_frame, text="Blue", bg="blue", fg="white", command=lambda: self.engine.set_ambient_color(0, 0, 255)).pack(side="left", expand=True, fill="x", padx=2)

    def on_mode_change(self, event):
        new_mode = self.mode_var.get().lower()
        self.app_state.set_mode(new_mode)
        self.apply_mode(new_mode)
        
        # Update slider based on loaded settings
        self.brightness_var.set(self.app_state.get_current_settings().get("brightness_limit", 1.0) * 100)

    def on_brightness_change(self, val):
        limit = float(val) / 100.0
        self.app_state.settings[self.app_state.mode]["brightness_limit"] = limit
        self.app_state.save()

    def apply_mode(self, mode):
        # Stop all analyzers first
        self.screen_analyzer.stop()
        self.audio_analyzer.stop()
        self.music_analyzer.stop()
        
        if mode in [AppMode.MOVIE, AppMode.DEVELOPER, AppMode.GAME]:
            self.screen_analyzer.start()
            self.audio_analyzer.start()
        elif mode == AppMode.MUSIC:
            self.music_analyzer.start()
        elif mode == AppMode.CUSTOM:
            # Custom logic could be added here, e.g., solid color
            s = self.app_state.settings[AppMode.CUSTOM]
            self.engine.set_ambient_color(s.get('r',255), s.get('g',255), s.get('b',255))
            self.engine.set_ambient_brightness(1.0) # Solid brightness

    def update_diagnostics(self):
        try:
            metrics = diag.diagnostics.get_metrics()
            status_text = "Status: ● Connected" if metrics.get("esp32_connected") else "Status: ○ Disconnected"
            fps = metrics.get("render_fps", 0)
            self.status_var.set(f"{status_text} | FPS: {fps:.1f}")
        except Exception:
            pass
        self.root.after(500, self.update_diagnostics)

    def on_closing(self):
        self.screen_analyzer.stop()
        self.audio_analyzer.stop()
        self.music_analyzer.stop()
        self.dev_events.stop()
        self.engine.stop()
        self.transport.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DevLightsApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
