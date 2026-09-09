import time
import threading
from lighting_state import LightingState, EventPriority

class PriorityManager:
    """Handles stacking and restoration of temporary events (like developer builds)."""
    def __init__(self):
        self.base_state = LightingState()
        self.active_event = None
        
    def set_base_state(self, r, g, b, brightness):
        self.base_state.r = r
        self.base_state.g = g
        self.base_state.b = b
        self.base_state.brightness = brightness
        
    def set_event(self, state: LightingState, duration: float):
        # Only override if new event priority is >= current event (if any)
        if not self.active_event or state.priority.value >= self.active_event.priority.value:
            state.expiration = time.time() + duration
            self.active_event = state
            
    def get_current_target(self) -> LightingState:
        if self.active_event:
            if time.time() > self.active_event.expiration:
                self.active_event = None # Expired
            else:
                return self.active_event
        return self.base_state

class LightingEngine:
    def __init__(self, transport, app_state=None):
        self.transport = transport
        self.app_state = app_state
        self.priority_manager = PriorityManager()
        
        self.smoothing_factor = 0.8
        self.brightness_ceiling = 1.0
        
        # We store the smoothed, currently-rendered values
        self.render_state = LightingState()
        self.user_intensity = 1.0 # 0.0 to 1.0
        
        self.state_lock = threading.Lock()
        self.running = True
        self.render_thread = threading.Thread(target=self._render_loop, daemon=True)
        self.render_thread.start()

    def set_ambient_color(self, r: int, g: int, b: int):
        with self.state_lock:
            self.priority_manager.base_state.r = r
            self.priority_manager.base_state.g = g
            self.priority_manager.base_state.b = b

    def set_ambient_brightness(self, intensity_0_to_1: float):
        self.user_intensity = max(0.0, min(1.0, intensity_0_to_1))
        
        limit = self.brightness_ceiling
        if self.app_state:
            limit = self.app_state.get_current_settings().get("brightness_limit", self.brightness_ceiling)
        
        final_brightness = int(self.user_intensity * limit * 255)
        
        with self.state_lock:
            self.priority_manager.base_state.brightness = final_brightness

    def trigger_event(self, r: int, g: int, b: int, duration_sec: float, priority: EventPriority):
        event_state = LightingState(r=r, g=g, b=b, brightness=255, priority=priority)
        with self.state_lock:
            self.priority_manager.set_event(event_state, duration_sec)

    def stop(self):
        self.running = False
        if self.transport:
            self.transport.disconnect()

    def _render_loop(self):
        # Run rendering independently from input ingestion.
        # While true 60Hz depends on the OS and locks, this targets 16.6ms intervals.
        target_fps = 60
        frame_time = 1.0 / target_fps
        
        while self.running:
            start_time = time.time()
            
            with self.state_lock:
                target_state = self.priority_manager.get_current_target()
                target_r = target_state.r
                target_g = target_state.g
                target_b = target_state.b
                target_bright = target_state.brightness
            
            # Apply smoothing outside the lock
            smooth = self.smoothing_factor
            if self.app_state:
                settings = self.app_state.get_current_settings()
                smooth = settings.get("smoothing", self.smoothing_factor)
                
            self.render_state.r = int((target_r * (1 - smooth)) + (self.render_state.r * smooth))
            self.render_state.g = int((target_g * (1 - smooth)) + (self.render_state.g * smooth))
            self.render_state.b = int((target_b * (1 - smooth)) + (self.render_state.b * smooth))
            self.render_state.brightness = int((target_bright * (1 - smooth)) + (self.render_state.brightness * smooth))
            self.render_state.validate()

            transport_start = time.time()
            if self.transport:
                self.transport.send_state(
                    self.render_state.r,
                    self.render_state.g,
                    self.render_state.b,
                    self.render_state.brightness
                )
            transport_ms = (time.time() - transport_start) * 1000.0
            
            import diagnostics as diag
            diag.diagnostics.record_frame()
            diag.diagnostics.set_metric("transport_ms", transport_ms)
            diag.diagnostics.set_metric("current_rgb", (self.render_state.r, self.render_state.g, self.render_state.b))
            diag.diagnostics.set_metric("current_brightness", self.render_state.brightness)
            if self.transport:
                diag.diagnostics.set_metric("esp32_connected", self.transport.is_connected())
                diag.diagnostics.set_metric("transport_type", self.transport.__class__.__name__)
                
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_time - elapsed)
            time.sleep(sleep_time)
