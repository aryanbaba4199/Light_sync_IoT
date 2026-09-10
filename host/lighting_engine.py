import time
import threading
from typing import List, Tuple
from lighting_state import LightingState, EventPriority
from music_models import LED_COUNT, MusicAnalysis, MusicMapping
from music_mapping_engine import MusicMappingEngine

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
        
        self.led_count = getattr(app_state, "led_count", LED_COUNT)
        self.music_mapping_engine = MusicMappingEngine(led_count=self.led_count)
        self.latest_music_analysis = MusicAnalysis()
        
        self.smoothing_factor = 0.8
        self.render_state = LightingState()
        self.led_frame: List[Tuple[int, int, int]] = [(0, 0, 0)] * self.led_count
        
        # User state (from slider)
        self.user_brightness = 1.0 
        
        # Mode state (from analyzers)
        self.mode_intensity = 1.0
        
        self.state_lock = threading.Lock()
        self.running = True
        self.render_thread = threading.Thread(target=self._render_loop, daemon=True)
        self.render_thread.start()

    def process_music_analysis(self, analysis: MusicAnalysis):
        """Called by MusicAnalyzer when a new audio feature packet is computed."""
        with self.state_lock:
            self.latest_music_analysis = analysis

    def set_ambient_color(self, r: int, g: int, b: int):
        with self.state_lock:
            self.priority_manager.base_state.r = r
            self.priority_manager.base_state.g = g
            self.priority_manager.base_state.b = b

    def set_ambient_brightness(self, intensity_0_to_1: float):
        """Called by analyzers to set dynamic intensity (e.g. movie brightness)"""
        with self.state_lock:
            self.mode_intensity = max(0.0, min(1.0, intensity_0_to_1))
            
    def set_user_brightness(self, brightness_0_to_1: float):
        """Called by websocket when user drags the brightness slider"""
        with self.state_lock:
            self.user_brightness = max(0.0, min(1.0, brightness_0_to_1))

    def trigger_event(self, r: int, g: int, b: int, duration_sec: float, priority: EventPriority):
        event_state = LightingState(r=r, g=g, b=b, brightness=255, priority=priority)
        with self.state_lock:
            self.priority_manager.set_event(event_state, duration_sec)

    def reset_state(self):
        """Clears all frames, resets smoothing buffers, and forces a blackout flush."""
        with self.state_lock:
            self.render_state = LightingState()
            self.led_frame = [(0, 0, 0)] * self.led_count
            self.latest_music_analysis = MusicAnalysis()
        if self.transport:
            try:
                self.transport.send_zones([])
                self.transport.send_state(0, 0, 0, 0)
            except Exception as e:
                print(f"[LightingEngine] reset_state transport flush: {e}")

    def stop(self):
        self.running = False
        if self.transport:
            self.transport.disconnect()

    def _render_loop(self):
        target_fps = 30
        frame_time = 1.0 / target_fps
        last_wake_time = time.time()
        
        while self.running:
            start_time = time.time()
            
            # MACOS SLEEP DETECTION:
            # If the loop pauses for more than 3 seconds, the OS went to sleep
            if start_time - last_wake_time > 3.0:
                print("WOKE FROM SLEEP! Reconnecting transport...")
                if self.transport:
                    self.transport.disconnect()
            last_wake_time = start_time
            
            with self.state_lock:
                target_state = self.priority_manager.get_current_target()
                target_r = target_state.r
                target_g = target_state.g
                target_b = target_state.b
                
                user_bright = self.user_brightness
                mode_int = self.mode_intensity
                analysis = self.latest_music_analysis
                
                if self.priority_manager.active_event:
                    mode_int = 1.0 
            
            smooth = self.smoothing_factor
            mode_limit = 1.0
            power_on = True
            current_mode = "custom"
            
            if self.app_state:
                current_mode = self.app_state.mode
                settings = self.app_state.get_current_settings()
                smooth = settings.get("smoothing", self.smoothing_factor)
                mode_limit = settings.get("brightness_limit", 1.0)
                power_on = self.app_state.power_on

            # ==========================================
            # RENDER PIPELINE
            # ==========================================
            transport_start = time.time()

            if current_mode == "music":
                # MUSIC MODE: Multi-zone & independent instrument rendering
                raw_mappings = self.app_state.get_music_mappings() if self.app_state else []
                mappings = [MusicMapping.from_dict(m) for m in raw_mappings]
                response_mode = self.app_state.get_music_response_mode() if self.app_state else "flash"

                # Render 300-LED frame buffer
                frame = self.music_mapping_engine.render_frame(
                    analysis=analysis,
                    mappings=mappings,
                    user_brightness=user_bright,
                    mode_limit=mode_limit,
                    power_on=power_on,
                    response_mode=response_mode
                )
                self.led_frame = frame

                # Protocol V2: Extract zones for compact serial transmission
                zones = self.music_mapping_engine.extract_zones_for_protocol(
                    analysis=analysis,
                    mappings=mappings,
                    user_brightness=user_bright,
                    mode_limit=mode_limit,
                    power_on=power_on,
                    response_mode=response_mode
                )

                if self.transport:
                    self.transport.send_zones(zones)
                    self.transport.send_frame(self.led_frame)

                # Compute representative color for virtual UI / status metrics
                active_colors = [c for c in frame if c != (0, 0, 0)]
                if active_colors:
                    avg_r = int(sum(c[0] for c in active_colors) / len(active_colors))
                    avg_g = int(sum(c[1] for c in active_colors) / len(active_colors))
                    avg_b = int(sum(c[2] for c in active_colors) / len(active_colors))
                    avg_bright = int(max(avg_r, avg_g, avg_b))
                else:
                    avg_r, avg_g, avg_b, avg_bright = 0, 0, 0, 0

                self.render_state.r = avg_r
                self.render_state.g = avg_g
                self.render_state.b = avg_b
                self.render_state.brightness = avg_bright

            else:
                # SINGLE-STATE MODES (Custom, Movie, Game, Developer):
                # Preserves 100% backward compatibility
                if not power_on:
                    final_target_bright = 0.0
                else:
                    final_target_bright = mode_int * mode_limit * user_bright * 255.0
                    
                self.render_state.r = int((target_r * (1 - smooth)) + (self.render_state.r * smooth))
                self.render_state.g = int((target_g * (1 - smooth)) + (self.render_state.g * smooth))
                self.render_state.b = int((target_b * (1 - smooth)) + (self.render_state.b * smooth))
                self.render_state.brightness = int((final_target_bright * (1 - smooth)) + (self.render_state.brightness * smooth))
                self.render_state.validate()

                # Single color fill across full frame buffer
                c_rgb = (
                    int(self.render_state.r * (self.render_state.brightness / 255.0)),
                    int(self.render_state.g * (self.render_state.brightness / 255.0)),
                    int(self.render_state.b * (self.render_state.brightness / 255.0))
                )
                self.led_frame = [c_rgb] * self.led_count

                if self.transport:
                    # Protocol V1 transmission
                    self.transport.send_state(
                        self.render_state.r,
                        self.render_state.g,
                        self.render_state.b,
                        self.render_state.brightness
                    )
                    self.transport.send_frame(self.led_frame)

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
