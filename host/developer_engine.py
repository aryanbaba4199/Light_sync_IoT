import time
import math
import threading
from typing import Dict, List, Optional, Tuple, Any

from developer_models import (
    DeveloperEventType,
    DeveloperState,
    DeveloperPriority,
    DeveloperEvent,
    DeveloperZone,
    DeveloperLayout,
    get_event_profile,
)

class DeveloperEventManager:
    """
    Thread-safe manager for Developer Mode persistent state and transient events.
    Separates persistent state (IDLE, CODING, BUILDING, TESTING, DEPLOYING)
    from transient event visual effects.
    """
    def __init__(self, default_layout: Optional[DeveloperLayout] = None):
        self._lock = threading.Lock()
        self._state: DeveloperState = DeveloperState.IDLE
        self._active_event: Optional[DeveloperEvent] = None
        self._layout: DeveloperLayout = default_layout or DeveloperLayout.default()
        self._last_state_change: float = time.time()

    @property
    def layout(self) -> DeveloperLayout:
        with self._lock:
            return self._layout

    def set_layout(self, layout: DeveloperLayout):
        with self._lock:
            self._layout = layout

    def get_state(self) -> DeveloperState:
        with self._lock:
            return self._state

    def set_state(self, state: DeveloperState):
        with self._lock:
            self._state = state
            self._last_state_change = time.time()

    def get_active_event(self) -> Optional[DeveloperEvent]:
        with self._lock:
            if self._active_event is not None:
                if self._active_event.is_expired():
                    self._active_event = None
                else:
                    return self._active_event
            return None

    def reset_transient_event(self):
        """Clears any active transient event (used on mode transitions or timeout)."""
        with self._lock:
            self._active_event = None

    def reset_all(self):
        """Resets persistent state to IDLE and clears transient events."""
        with self._lock:
            self._state = DeveloperState.IDLE
            self._active_event = None
            self._last_state_change = time.time()

    def handle_event(
        self,
        event_input: Any,
        priority: Optional[DeveloperPriority] = None,
        duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Validates, updates persistent state, and sets transient event if priority allows.
        Returns: (success, error_message, state_dict)
        """
        # Resolve event type
        if isinstance(event_input, DeveloperEventType):
            event_type = event_input
        elif isinstance(event_input, str):
            event_type = DeveloperEventType.from_string(event_input)
            if not event_type:
                return False, f"Unknown developer event: '{event_input}'", {}
        else:
            return False, f"Invalid event type object: {type(event_input)}", {}

        # Default profile for priority, duration, target_zone
        default_priority, default_duration, default_zone = get_event_profile(event_type)
        final_priority = priority if priority is not None else default_priority
        final_duration = duration if duration is not None else default_duration
        meta = dict(metadata or {})
        if default_zone and "zone" not in meta:
            meta["zone"] = default_zone

        now = time.time()
        new_event = DeveloperEvent(
            event_type=event_type,
            priority=final_priority,
            duration=final_duration,
            timestamp=now,
            metadata=meta
        )

        with self._lock:
            # 1. Update Persistent State transitions
            if event_type == DeveloperEventType.BUILD_STARTED:
                self._state = DeveloperState.BUILDING
            elif event_type in (DeveloperEventType.BUILD_SUCCESS, DeveloperEventType.BUILD_FAILED):
                self._state = DeveloperState.IDLE
            elif event_type == DeveloperEventType.TEST_STARTED:
                self._state = DeveloperState.TESTING
            elif event_type in (DeveloperEventType.TEST_SUCCESS, DeveloperEventType.TEST_FAILED):
                self._state = DeveloperState.IDLE
            elif event_type == DeveloperEventType.DEPLOY_STARTED:
                self._state = DeveloperState.DEPLOYING
            elif event_type in (DeveloperEventType.DEPLOY_SUCCESS, DeveloperEventType.DEPLOY_FAILED):
                self._state = DeveloperState.IDLE
            elif event_type in (DeveloperEventType.CODE_ACTIVE, DeveloperEventType.CODING_ACTIVITY, DeveloperEventType.FILE_SAVED):
                self._state = DeveloperState.CODING
            elif event_type == DeveloperEventType.SERVER_STOPPED:
                self._state = DeveloperState.IDLE

            self._last_state_change = now

            # 2. Update Transient Event based on priority
            should_set = False
            if self._active_event is None or self._active_event.is_expired(now):
                should_set = True
            elif new_event.priority >= self._active_event.priority:
                should_set = True

            if should_set:
                self._active_event = new_event

            result = {
                "event": new_event.to_dict(),
                "developer_state": self._state.value,
                "event_accepted": should_set
            }

        return True, None, result


class DeveloperRenderer:
    """
    Time-based procedural effect engine for Developer Mode.
    Produces a 300-LED frame buffer (List[Tuple[int, int, int]]) based on:
      - Total LED count (default 300)
      - Persistent developer state (IDLE, CODING, BUILDING, TESTING, DEPLOYING)
      - Active transient developer event (with automatic decay back to persistent state)
      - Developer zone layout
      - Global brightness & mode limit
      - Power state (strictly all black when OFF)
    """
    def __init__(self, led_count: int = 300):
        self.led_count = led_count

    def render(
        self,
        state: DeveloperState,
        active_event: Optional[DeveloperEvent],
        layout: Optional[DeveloperLayout] = None,
        global_brightness: float = 1.0,
        mode_limit: float = 1.0,
        power_on: bool = True,
        current_time: Optional[float] = None
    ) -> List[Tuple[int, int, int]]:
        """
        Renders the full 300-LED array smoothly as time advances.
        """
        if not power_on or self.led_count <= 0:
            return [(0, 0, 0)] * self.led_count

        brightness_scale = max(0.0, min(1.0, global_brightness * mode_limit))
        if brightness_scale <= 0.0:
            return [(0, 0, 0)] * self.led_count

        t = current_time if current_time is not None else time.time()
        N = self.led_count
        raw_frame = [(0, 0, 0)] * N

        # =================================================================
        # 1. PERSISTENT STATE PROCEDURAL VISUALS
        # =================================================================
        if state == DeveloperState.IDLE:
            # Subtle dim blue/cyan breathing with slow spatial drift
            breath = 0.5 + 0.5 * math.sin(2.0 * math.pi * 0.20 * t)  # 5-second breath period
            for i in range(N):
                spatial = 0.5 + 0.5 * math.sin(2.0 * math.pi * ((i / float(N)) * 1.5 - 0.10 * t))
                v = 0.25 + 0.75 * (0.65 * breath + 0.35 * spatial)
                # Dim cyan/blue baseline: alive and calm
                r = 0
                g = int(28 * v)
                b = int(60 * v)
                raw_frame[i] = (r, g, b)

        elif state == DeveloperState.CODING:
            # Flowing activity effect: smooth blue/cyan wave
            for i in range(N):
                w1 = 0.5 + 0.5 * math.sin(2.0 * math.pi * (i / 45.0 - 0.9 * t))
                w2 = 0.5 + 0.5 * math.sin(2.0 * math.pi * (i / 90.0 + 0.4 * t))
                blend = 0.65 * w1 + 0.35 * w2
                r = 0
                g = int(30 + 130 * blend)
                b = int(70 + 180 * blend)
                raw_frame[i] = (r, g, b)

        elif state == DeveloperState.BUILDING:
            # Active blue visualization: moving blue sweep / progress beam
            beam_pos = (t * 90.0) % N  # Sweep at 90 LEDs/sec
            beam_width = 35.0
            for i in range(N):
                dist = (i - beam_pos) % N
                if dist < beam_width:
                    pulse = (1.0 - dist / beam_width) ** 1.8
                    r = int(10 + 30 * pulse)
                    g = int(30 + 130 * pulse)
                    b = int(80 + 175 * pulse)
                else:
                    r, g, b = 5, 20, 60
                raw_frame[i] = (r, g, b)

        elif state == DeveloperState.TESTING:
            # Active purple/magenta visualization: ping-pong scanning pattern
            cycle = (t / 2.2) % 2.0  # 2.2 sec one-way scan
            head_pos = (cycle if cycle <= 1.0 else 2.0 - cycle) * (N - 1)
            scan_width = 30.0
            for i in range(N):
                dist = abs(i - head_pos)
                if dist < scan_width:
                    pulse = (1.0 - dist / scan_width) ** 1.5
                    r = int(60 + 170 * pulse)
                    g = int(5 + 25 * pulse)
                    b = int(80 + 175 * pulse)
                else:
                    r, g, b = 35, 5, 50
                raw_frame[i] = (r, g, b)

        elif state == DeveloperState.DEPLOYING:
            # Active cyan visualization: moving cyan sweep wave
            wave_pos = (t * 130.0) % N
            trail_len = 45.0
            for i in range(N):
                dist = (i - wave_pos) % N
                if dist < trail_len:
                    pulse = (1.0 - dist / trail_len) ** 1.6
                    r = int(5 + 20 * pulse)
                    g = int(40 + 190 * pulse)
                    b = int(70 + 185 * pulse)
                else:
                    r, g, b = 0, 30, 50
                raw_frame[i] = (r, g, b)

        # =================================================================
        # 2. TRANSIENT DEVELOPER EVENT PROCEDURAL ANIMATIONS
        # =================================================================
        if active_event is not None and not active_event.is_expired(t):
            elapsed = t - active_event.timestamp
            dur = max(0.001, active_event.duration)
            progress = max(0.0, min(1.0, elapsed / dur))
            fade = 1.0 - progress
            ev_type = active_event.event_type

            # --- A. SUCCESS EVENTS (Green confirmation sweep / expanding pulse) ---
            if ev_type in (
                DeveloperEventType.BUILD_SUCCESS,
                DeveloperEventType.TEST_SUCCESS,
                DeveloperEventType.DEPLOY_SUCCESS,
                DeveloperEventType.PR_MERGED,
            ):
                # Expanding wave front across the strip
                sweep_head = progress * N * 1.2
                for i in range(N):
                    if i <= sweep_head:
                        # Warm bright green glow fading into state
                        green_intensity = fade * max(0.0, min(1.0, 1.0 - (sweep_head - i) / 120.0))
                        gr = int(0)
                        gg = int(255 * fade)
                        gb = int(60 * fade)
                        base_r, base_g, base_b = raw_frame[i]
                        raw_frame[i] = (
                            max(base_r, gr),
                            max(base_g, gg),
                            max(base_b, gb)
                        )

            # --- B. FAILURE / ERROR EVENTS (3-pulse red strobe flash) ---
            elif ev_type in (
                DeveloperEventType.BUILD_FAILED,
                DeveloperEventType.TEST_FAILED,
                DeveloperEventType.DEPLOY_FAILED,
                DeveloperEventType.ERROR,
                DeveloperEventType.SERVER_ERROR,
                DeveloperEventType.CODE_ERROR,
            ):
                # 3 sharp pulses decaying over the event duration
                strobe = abs(math.sin(progress * 3.0 * math.pi)) ** 1.6
                intensity = strobe * (0.35 + 0.65 * fade)
                red_val = int(255 * intensity)
                for i in range(N):
                    base_r, base_g, base_b = raw_frame[i]
                    raw_frame[i] = (
                        max(base_r, red_val),
                        int(base_g * (1.0 - intensity * 0.8)),
                        int(base_b * (1.0 - intensity * 0.8))
                    )

            # --- C. WARNING EVENTS (Orange/amber pulse) ---
            elif ev_type in (
                DeveloperEventType.WARNING,
                DeveloperEventType.CODE_WARNING,
                DeveloperEventType.SERVER_STOPPED,
            ):
                # 2 smooth orange/yellow pulses
                pulse = abs(math.sin(progress * 2.0 * math.pi)) * fade
                wr = int(255 * pulse)
                wg = int(140 * pulse)
                wb = 0
                for i in range(N):
                    base_r, base_g, base_b = raw_frame[i]
                    raw_frame[i] = (
                        max(base_r, wr),
                        max(base_g, wg),
                        max(base_b, wb)
                    )

            # --- D. GIT EVENTS (Short cyan / blue pulses & sweeps) ---
            elif ev_type == DeveloperEventType.GIT_COMMIT:
                # Short cyan pulse expanding across strip
                pulse = (fade ** 2.0)
                cr, cg, cb = 0, int(220 * pulse), int(255 * pulse)
                for i in range(N):
                    base_r, base_g, base_b = raw_frame[i]
                    raw_frame[i] = (max(base_r, cr), max(base_g, cg), max(base_b, cb))

            elif ev_type == DeveloperEventType.GIT_PUSH:
                # Fast cyan sweep from 0 to 299
                sweep_head = progress * N
                trail = 40.0
                for i in range(N):
                    dist = abs(i - sweep_head)
                    if dist < trail:
                        factor = ((1.0 - dist / trail) ** 1.5) * fade
                        cr, cg, cb = 0, int(230 * factor), int(255 * factor)
                        base_r, base_g, base_b = raw_frame[i]
                        raw_frame[i] = (max(base_r, cr), max(base_g, cg), max(base_b, cb))

            elif ev_type == DeveloperEventType.PR_CREATED:
                # Dual blue/cyan pulses meeting at center
                center = N / 2.0
                dist_from_edge = progress * center
                for i in range(N):
                    d1 = abs(i - dist_from_edge)
                    d2 = abs(i - (N - 1 - dist_from_edge))
                    close_d = min(d1, d2)
                    if close_d < 25.0:
                        factor = ((1.0 - close_d / 25.0) ** 1.5) * fade
                        cr, cg, cb = 0, int(180 * factor), int(255 * factor)
                        base_r, base_g, base_b = raw_frame[i]
                        raw_frame[i] = (max(base_r, cr), max(base_g, cg), max(base_b, cb))

            # --- E. CODING ACTIVITY / FILE SAVED (Short bright activity pulse) ---
            elif ev_type in (DeveloperEventType.CODING_ACTIVITY, DeveloperEventType.FILE_SAVED, DeveloperEventType.CODE_ACTIVE):
                pulse = (fade ** 2.5)
                cr, cg, cb = 0, int(150 * pulse), int(220 * pulse)
                for i in range(N):
                    base_r, base_g, base_b = raw_frame[i]
                    raw_frame[i] = (max(base_r, cr), max(base_g, cg), max(base_b, cb))

            elif ev_type == DeveloperEventType.BUILD_STARTED:
                # Immediate bright amber/blue head sweep
                sweep_head = (progress * N * 1.5) % N
                for i in range(N):
                    dist = abs(i - sweep_head)
                    if dist < 30.0:
                        factor = ((1.0 - dist / 30.0) ** 1.4) * fade
                        ar, ag, ab = int(255 * factor), int(160 * factor), int(20 * factor)
                        base_r, base_g, base_b = raw_frame[i]
                        raw_frame[i] = (max(base_r, ar), max(base_g, ag), max(base_b, ab))

            elif ev_type == DeveloperEventType.TEST_STARTED:
                # Immediate bright purple/magenta wave
                sweep_head = (progress * N * 1.5) % N
                for i in range(N):
                    dist = abs(i - sweep_head)
                    if dist < 30.0:
                        factor = ((1.0 - dist / 30.0) ** 1.4) * fade
                        pr, pg, pb = int(220 * factor), int(30 * factor), int(255 * factor)
                        base_r, base_g, base_b = raw_frame[i]
                        raw_frame[i] = (max(base_r, pr), max(base_g, pg), max(base_b, pb))

            elif ev_type == DeveloperEventType.DEPLOY_STARTED:
                # Immediate bright cyan/teal wave
                sweep_head = (progress * N * 1.5) % N
                for i in range(N):
                    dist = abs(i - sweep_head)
                    if dist < 30.0:
                        factor = ((1.0 - dist / 30.0) ** 1.4) * fade
                        dr, dg, db = 0, int(240 * factor), int(255 * factor)
                        base_r, base_g, base_b = raw_frame[i]
                        raw_frame[i] = (max(base_r, dr), max(base_g, dg), max(base_b, db))

        # =================================================================
        # 3. GLOBAL BRIGHTNESS & POWER SCALING
        # =================================================================
        final_frame: List[Tuple[int, int, int]] = []
        for r, g, b in raw_frame:
            sr = max(0, min(255, int(r * brightness_scale)))
            sg = max(0, min(255, int(g * brightness_scale)))
            sb = max(0, min(255, int(b * brightness_scale)))
            final_frame.append((sr, sg, sb))

        return final_frame

    def extract_zones_for_protocol(
        self,
        frame: List[Tuple[int, int, int]],
        layout: Optional[DeveloperLayout] = None
    ) -> List[dict]:
        """
        Extracts compact hardware zones for Protocol V2 (0x56) transmission.
        Enforces zone count <= 42 for ESP32 UART firmware limits.
        Chunks the 300-LED strip into 25 contiguous hardware zones:
        {"start": s, "end": e, "r": r, "g": g, "b": b}
        """
        total = len(frame)
        if total == 0:
            return []

        # 1. Single uniform color check (e.g. solid flash or blackout)
        first_c = frame[0]
        if all(c == first_c for c in frame):
            return [{"start": 0, "end": total - 1, "r": first_c[0], "g": first_c[1], "b": first_c[2]}]

        # 2. 25-zone chunking for continuous spatial effects across 300 LEDs
        num_zones = 25
        chunk_size = total / float(num_zones)
        zones = []
        for k in range(num_zones):
            s = int(k * chunk_size)
            e = min(total - 1, int((k + 1) * chunk_size) - 1)
            slice_leds = frame[s : e + 1]
            if slice_leds:
                zr = int(sum(c[0] for c in slice_leds) / len(slice_leds))
                zg = int(sum(c[1] for c in slice_leds) / len(slice_leds))
                zb = int(sum(c[2] for c in slice_leds) / len(slice_leds))
            else:
                zr, zg, zb = 0, 0, 0
            zones.append({"start": s, "end": e, "r": zr, "g": zg, "b": zb})

        return zones
