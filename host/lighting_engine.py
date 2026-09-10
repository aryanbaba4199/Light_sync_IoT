import time
import threading
from typing import List, Tuple, Optional
import numpy as np
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
        
        # Movie Mode Spatial Frame Buffer
        self.latest_movie_frame: Optional[List[Tuple[int, int, int]]] = None
        self.latest_movie_edges: dict = {}
        self.smooth_music_multiplier = 1.0

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

    def process_movie_frame(self, led_colors: List[Tuple[int, int, int]], edge_stats: dict = None):
        """Called by ScreenAnalyzer when a new spatial movie frame is sampled."""
        with self.state_lock:
            self.latest_movie_frame = led_colors
            self.latest_movie_edges = edge_stats or {}

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
            self.latest_movie_frame = None
            self.latest_movie_edges = {}
            self.smooth_music_multiplier = 1.0
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

    def _extract_movie_zones(self, rendered_frame: List[Tuple[int, int, int]]) -> List[dict]:
        """
        Extracts up to 24-30 contiguous spatial zones for Protocol V2 hardware transmission
        (ESP32 zone count limit is 42).
        """
        zones = []
        frame_len = len(rendered_frame)
        if frame_len == 0:
            return zones

        edge_subdivisions = {"top": 8, "right": 4, "bottom": 8, "left": 4}
        edge_ranges = None
        if self.app_state and hasattr(self.app_state, "get_movie_layout"):
            layout = self.app_state.get_movie_layout()
            edge_ranges = layout.get_edge_ranges()

        if edge_ranges:
            for edge_name, max_subs in edge_subdivisions.items():
                s_edge, e_edge = edge_ranges.get(edge_name, (0, 0))
                edge_len = e_edge - s_edge
                if edge_len <= 0 or s_edge >= frame_len:
                    continue

                actual_end = min(frame_len, e_edge)
                edge_len = actual_end - s_edge
                num_subs = max(1, min(max_subs, edge_len))
                chunk_size = edge_len / num_subs

                for k in range(num_subs):
                    zs = s_edge + int(k * chunk_size)
                    ze = s_edge + int((k + 1) * chunk_size) - 1
                    ze = max(zs, min(actual_end - 1, ze))
                    slice_colors = rendered_frame[zs : ze + 1]
                    if slice_colors:
                        zr = int(np.mean([c[0] for c in slice_colors]))
                        zg = int(np.mean([c[1] for c in slice_colors]))
                        zb = int(np.mean([c[2] for c in slice_colors]))
                    else:
                        zr, zg, zb = 0, 0, 0
                    zones.append({"start": zs, "end": ze, "r": zr, "g": zg, "b": zb})
        else:
            # Fallback: 24 uniform chunks across the frame
            num_chunks = min(24, frame_len)
            chunk_size = frame_len / num_chunks
            for k in range(num_chunks):
                zs = int(k * chunk_size)
                ze = min(frame_len - 1, int((k + 1) * chunk_size) - 1)
                slice_colors = rendered_frame[zs : ze + 1]
                zr = int(np.mean([c[0] for c in slice_colors]))
                zg = int(np.mean([c[1] for c in slice_colors]))
                zb = int(np.mean([c[2] for c in slice_colors]))
                zones.append({"start": zs, "end": ze, "r": zr, "g": zg, "b": zb})

        return zones

    def _render_loop(self):
        target_fps = 30
        frame_time = 1.0 / target_fps
        last_wake_time = time.time()
        
        while self.running:
            start_time = time.time()
            
            # MACOS SLEEP DETECTION:
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
                movie_frame = self.latest_movie_frame
                
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

            elif current_mode == "movie" and movie_frame is not None:
                # MOVIE MODE: Spatial perimeter rendering with optional Music Sync
                movie_settings = self.app_state.settings.get("movie", {}) if self.app_state else {}
                sync_music = bool(movie_settings.get("sync_music", False))
                min_bright = float(movie_settings.get("min_music_brightness", 0.35))
                max_bright = float(movie_settings.get("max_music_brightness", 1.00))

                if sync_music and analysis.music_gate_open:
                    # Music density modulates intensity; colors are strictly from video
                    density = 0.60 * analysis.overall + 0.25 * analysis.beat + 0.15 * analysis.bass_transient
                    target_mult = min_bright + (max_bright - min_bright) * min(1.0, max(0.0, density))
                    rate = 0.40 if target_mult > self.smooth_music_multiplier else 0.15
                    self.smooth_music_multiplier = self.smooth_music_multiplier * (1.0 - rate) + target_mult * rate
                    music_mult = self.smooth_music_multiplier
                elif sync_music and not analysis.music_gate_open:
                    # Quiet room / silence: settle to min_bright floor smoothly
                    rate = 0.15
                    self.smooth_music_multiplier = self.smooth_music_multiplier * (1.0 - rate) + min_bright * rate
                    music_mult = self.smooth_music_multiplier
                else:
                    self.smooth_music_multiplier = 1.0
                    music_mult = 1.0

                if not power_on:
                    final_scalar = 0.0
                else:
                    final_scalar = user_bright * mode_limit * music_mult

                frame_len = len(movie_frame)
                rendered_frame = []
                for i in range(self.led_count):
                    if i < frame_len:
                        vr, vg, vb = movie_frame[i]
                    else:
                        vr, vg, vb = 0, 0, 0
                    r = int(min(255, max(0, vr * final_scalar)))
                    g = int(min(255, max(0, vg * final_scalar)))
                    b = int(min(255, max(0, vb * final_scalar)))
                    rendered_frame.append((r, g, b))
                self.led_frame = rendered_frame

                # Protocol V2: Extract compact perimeter zones for hardware
                zones = self._extract_movie_zones(rendered_frame)

                if self.transport:
                    self.transport.send_zones(zones)
                    self.transport.send_frame(self.led_frame)

                # Representative color for virtual UI / status metrics
                active_colors = [c for c in rendered_frame if c != (0, 0, 0)]
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
                # SINGLE-STATE MODES (Custom, Game, Developer, or initial Movie fallback):
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
            
            try:
                import diagnostics as diag
                diag.diagnostics.record_frame()
                diag.diagnostics.set_metric("transport_ms", transport_ms)
                diag.diagnostics.set_metric("current_rgb", (self.render_state.r, self.render_state.g, self.render_state.b))
                diag.diagnostics.set_metric("current_brightness", self.render_state.brightness)
                if current_mode == "movie":
                    diag.diagnostics.set_metric("movie_music_multiplier", round(self.smooth_music_multiplier, 3))
                if self.transport:
                    diag.diagnostics.set_metric("esp32_connected", self.transport.is_connected())
                    diag.diagnostics.set_metric("transport_type", self.transport.__class__.__name__)
            except Exception:
                pass
                
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_time - elapsed)
            time.sleep(sleep_time)
