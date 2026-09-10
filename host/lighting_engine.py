import time
import threading
from lighting_state import LightingState, EventPriority

class PriorityManager:
    def __init__(self):
        self.base_state = LightingState()
        self.active_event = None
        
    def set_base_state(self, r, g, b, brightness):
        self.base_state.r = r
        self.base_state.g = g
        self.base_state.b = b
        self.base_state.brightness = brightness
        
    def set_event(self, state: LightingState, duration: float):
        if not self.active_event or state.priority.value >= self.active_event.priority.value:
            state.expiration = time.time() + duration
            self.active_event = state
            
    def get_current_target(self) -> LightingState:
        if self.active_event:
            if time.time() > self.active_event.expiration:
                self.active_event = None
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
        
        self.render_state = LightingState()
        self.user_intensity = 1.0 
        
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
        target_fps = 15
        frame_time = 1.0 / target_fps
        
        while self.running:
            start_time = time.time()
            
            with self.state_lock:
                target_state = self.priority_manager.get_current_target()
                target_r = target_state.r
                target_g = target_state.g
                target_b = target_state.b
                target_bright = target_state.brightness
            
            smooth = self.smoothing_factor
            mode_limit = 1.0
            power_on = True
            
            if self.app_state:
                settings = self.app_state.get_current_settings()
                smooth = settings.get("smoothing", self.smoothing_factor)
                mode_limit = settings.get("brightness_limit", 1.0)
                power_on = self.app_state.power_on
                
            if not power_on:
                final_target_bright = 0
            else:
                final_target_bright = target_bright * mode_limit
                
            self.render_state.r = int((target_r * (1 - smooth)) + (self.render_state.r * smooth))
            self.render_state.g = int((target_g * (1 - smooth)) + (self.render_state.g * smooth))
            self.render_state.b = int((target_b * (1 - smooth)) + (self.render_state.b * smooth))
            self.render_state.brightness = int((final_target_bright * (1 - smooth)) + (self.render_state.brightness * smooth))
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
