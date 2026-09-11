import time
import threading

class Diagnostics:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Diagnostics, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.metrics = {
            "render_fps": 0.0,
            "capture_ms": 0.0,
            "audio_ms": 0.0,
            "transport_ms": 0.0,
            "dropped_frames": 0,
            "esp32_connected": False,
            "transport_type": "None",
            "current_mode": "None",
            "current_rgb": (0, 0, 0),
            "current_brightness": 0,
            "audio_noise_floor": 0.0,
            "audio_music_gate": False,
            "audio_kick_trigger": False,
            "audio_snare_trigger": False,
            "audio_clap_trigger": False,
            "audio_hihat_trigger": False,
            "audio_vocal_pitch": 0.0,
            "audio_vocal_confidence": 0.0,
            "audio_harmonic_ratio": 0.0
        }
        self._frame_times = []
        self._last_frame_time = time.time()
        self.lock = threading.Lock()

    def record_frame(self):
        now = time.time()
        dt = now - self._last_frame_time
        self._last_frame_time = now
        
        with self.lock:
            self._frame_times.append(dt)
            if len(self._frame_times) > 60:
                self._frame_times.pop(0)
            
            if self._frame_times:
                avg_dt = sum(self._frame_times) / len(self._frame_times)
                self.metrics["render_fps"] = 1.0 / avg_dt if avg_dt > 0 else 0.0

    def set_metric(self, key, value):
        with self.lock:
            if key in self.metrics:
                self.metrics[key] = value

    def get_metrics(self):
        with self.lock:
            return self.metrics.copy()

# Global accessor
diagnostics = Diagnostics()
