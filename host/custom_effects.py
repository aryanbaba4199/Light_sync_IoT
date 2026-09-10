"""
Custom Mode Multi-Effect Engine for DevLights.

Supports 10 high-performance procedural LED effects rendered on a 300-LED frame:
1. Rainfall (bounce 1->300->1 with fading gradient trail)
2. Flash (instant square wave with per-cycle color stability)
3. Random (stable random positions and colors with interval transitions)
4. Wave (smooth sinusoidal traveling wave)
5. Comet (bright head with decaying tail)
6. Breathing (smooth 0->100->0 easing)
7. Sparkle (ambient base with stochastic flare-ups and decaying lifetimes)
8. Color Chase (moving blocks of color groups with gaps)
9. Fire (organic procedural heat model with flame flicker)
10. Rainbow Flow (traveling continuous HSV rainbow)

All effects produce a List[Tuple[int, int, int]] of exactly 300 LEDs and respect
global user brightness, mode brightness limits, and power state.
"""
import time
import math
import random
import colorsys
import numpy as np
from typing import List, Tuple, Dict, Any, Optional

LED_COUNT = 300

# Default color constants
DEFAULT_BLUE = {"r": 0, "g": 120, "b": 255}
DEFAULT_RED = {"r": 255, "g": 0, "b": 0}
DEFAULT_GREEN = {"r": 0, "g": 255, "b": 0}
DEFAULT_PURPLE = {"r": 180, "g": 0, "b": 255}
DEFAULT_WHITE = {"r": 255, "g": 255, "b": 255}

DEFAULT_PALETTE = [
    {"r": 255, "g": 0, "b": 0},     # Red
    {"r": 255, "g": 120, "b": 0},   # Orange
    {"r": 255, "g": 255, "b": 0},   # Yellow
    {"r": 0, "g": 255, "b": 0},     # Green
    {"r": 0, "g": 150, "b": 255},   # Cyan
    {"r": 0, "g": 50, "b": 255},    # Blue
    {"r": 180, "g": 0, "b": 255},   # Purple
    {"r": 255, "g": 0, "b": 128},   # Magenta
]

DEFAULT_EFFECT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "static": {
        "color": DEFAULT_WHITE,
    },
    "rainfall": {
        "color": DEFAULT_BLUE,
        "speed": 50,              # 1 to 100
        "active_led_count": 10,   # 1 to 30
        "trail_length": 10,       # 1 to 30
    },
    "flash": {
        "color": DEFAULT_WHITE,
        "color_mode": "random",    # 'single', 'random', 'palette'
        "palette": DEFAULT_PALETTE,
        "speed": 40,              # Flash frequency (1 to 100)
    },
    "random": {
        "active_led_count": 20,   # 5 to 60
        "color_mode": "random",   # 'random', 'palette', 'single'
        "color": DEFAULT_PURPLE,
        "palette": DEFAULT_PALETTE,
        "speed": 35,              # Change interval (1 to 100)
        "fade": True,             # Smooth fade between transitions
        "min_brightness": 0.0,
        "max_brightness": 1.0,
    },
    "wave": {
        "color": DEFAULT_BLUE,
        "background_color": {"r": 0, "g": 10, "b": 40},
        "speed": 40,              # 1 to 100
        "width": 60,              # Wavelength in LEDs (20 to 150)
        "direction": "forward",   # 'forward', 'backward'
    },
    "comet": {
        "color": {"r": 0, "g": 220, "b": 255},
        "speed": 50,              # 1 to 100
        "tail_length": 25,        # 5 to 60
        "direction": "bounce",    # 'bounce', 'forward', 'backward'
    },
    "breathing": {
        "color": {"r": 255, "g": 60, "b": 0},
        "speed": 30,              # 1 to 100
        "min_brightness": 0.05,
        "max_brightness": 1.0,
    },
    "sparkle": {
        "color": DEFAULT_WHITE,
        "background_color": {"r": 10, "g": 10, "b": 25},
        "speed": 50,              # Spawn rate (1 to 100)
        "decay_rate": 0.15,
    },
    "color_chase": {
        "colors": [DEFAULT_RED, DEFAULT_GREEN, DEFAULT_BLUE, DEFAULT_PURPLE],
        "group_size": 15,
        "gap": 10,
        "speed": 45,
        "direction": "forward",
    },
    "fire": {
        "heat": 70,               # Fire intensity (20 to 100)
        "flicker": 60,            # 1 to 100
        "speed": 40,              # 1 to 100
        "brightness": 1.0,
    },
    "rainbow_flow": {
        "speed": 40,              # 1 to 100
        "wavelength": 150,        # Length of full spectrum in LEDs
        "saturation": 1.0,
        "brightness": 1.0,
        "direction": "forward",
    },
}


def _extract_rgb(val: Any, default=(255, 255, 255)) -> Tuple[int, int, int]:
    if isinstance(val, dict):
        return (
            int(val.get("r", default[0])),
            int(val.get("g", default[1])),
            int(val.get("b", default[2])),
        )
    elif isinstance(val, (list, tuple)) and len(val) >= 3:
        return (int(val[0]), int(val[1]), int(val[2]))
    return default


class CustomEffectEngine:
    """
    Stateful Procedural Animation Engine for Custom Mode.
    Called on each 30 FPS tick from LightingEngine._render_loop().
    """

    def __init__(self, led_count: int = LED_COUNT):
        self.led_count = led_count
        self.current_effect = "rainfall"
        self.configs: Dict[str, Dict[str, Any]] = {
            k: dict(v) for k, v in DEFAULT_EFFECT_CONFIGS.items()
        }

        # Internal state tracking
        self.start_time = time.time()
        self.last_time = time.time()

        # Flash state
        self.flash_cycle = -1
        self.flash_color = (255, 255, 255)

        # Random effect state
        self.random_cycle = -1
        self.random_positions: List[int] = []
        self.random_colors: List[Tuple[int, int, int]] = []
        self.random_prev_colors: List[Tuple[int, int, int]] = []
        self.random_cycle_start = 0.0

        # Sparkle state
        self.sparkles: List[Dict[str, Any]] = []  # {led: int, color: tuple, life: float}

        # Fire state (1D heat buffer)
        self.fire_heat = np.zeros(self.led_count, dtype=np.float32)

    def reset_state(self):
        self.start_time = time.time()
        self.last_time = time.time()
        self.flash_cycle = -1
        self.random_cycle = -1
        self.random_positions = []
        self.random_colors = []
        self.sparkles = []
        self.fire_heat = np.zeros(self.led_count, dtype=np.float32)

    def set_effect(self, effect_name: str, config: Optional[Dict[str, Any]] = None):
        effect_name = str(effect_name).lower()
        if effect_name not in DEFAULT_EFFECT_CONFIGS:
            effect_name = "rainfall"
        if effect_name != self.current_effect:
            self.current_effect = effect_name
            self.reset_state()
        if config:
            self.configs.setdefault(effect_name, {}).update(config)

    def get_config(self, effect_name: Optional[str] = None) -> Dict[str, Any]:
        effect = effect_name or self.current_effect
        return self.configs.get(effect, DEFAULT_EFFECT_CONFIGS.get(effect, {}))

    def update_config(self, effect_name: str, config: Dict[str, Any]):
        effect = str(effect_name).lower()
        if effect in DEFAULT_EFFECT_CONFIGS:
            self.configs.setdefault(effect, {}).update(config)

    # =========================================================================
    # EFFECT RENDERERS
    # =========================================================================

    def _render_rainfall(self, config: dict, t: float) -> List[Tuple[int, int, int]]:
        """
        LED 1 -> LED 300, then LED 300 -> LED 1, and repeat.
        Default 10 active LEDs with gradient trail [100%, 80%, 60%, 40%, 20%, 10%, 5%, 2%, 1%, 0%].
        """
        color = _extract_rgb(config.get("color", DEFAULT_BLUE))
        speed_raw = float(config.get("speed", 50))
        active_count = max(1, min(30, int(config.get("active_led_count", 10))))
        trail_length = max(1, min(30, int(config.get("trail_length", active_count))))

        # Trail decay weights (Head is 1.0, fading backwards)
        # e.g. for 10: [1.0, 0.8, 0.6, 0.4, 0.2, 0.1, 0.05, 0.02, 0.01, 0.0]
        trail_weights = []
        for k in range(trail_length):
            if k == 0:
                trail_weights.append(1.0)
            else:
                frac = k / trail_length
                trail_weights.append(max(0.01, math.exp(-2.8 * frac)))

        # Movement speed: LEDs per second (speed 50 = ~90 LEDs/sec)
        leds_per_sec = 15.0 + (speed_raw / 100.0) * 160.0
        # Travel span: distance between the two ends
        max_idx = self.led_count - 1
        cycle_distance = 2.0 * max_idx

        # Current continuous position along the cycle
        distance = (t * leds_per_sec) % cycle_distance

        if distance <= max_idx:
            # Moving forward (0 -> 299)
            head = distance
            direction = 1  # tail is behind head (lower indices)
        else:
            # Moving backward (299 -> 0)
            head = max_idx - (distance - max_idx)
            direction = -1  # tail is behind head (higher indices)

        frame = [(0, 0, 0)] * self.led_count

        # Paint active window
        for k, weight in enumerate(trail_weights[:active_count]):
            led_idx = int(round(head - direction * k))
            if 0 <= led_idx < self.led_count:
                r = int(color[0] * weight)
                g = int(color[1] * weight)
                b = int(color[2] * weight)
                frame[led_idx] = (r, g, b)

        return frame

    def _render_flash(self, config: dict, t: float) -> List[Tuple[int, int, int]]:
        """
        All 300 LEDs flash ON/OFF instantly in a square wave.
        Random colors are generated per flash cycle, not per frame.
        """
        speed_raw = float(config.get("speed", 40))
        color_mode = config.get("color_mode", "random")
        cfg_color = _extract_rgb(config.get("color", DEFAULT_WHITE))
        palette = [_extract_rgb(c) for c in config.get("palette", DEFAULT_PALETTE)]

        # Flash frequency: e.g. 0.5 to 5 Hz
        flash_freq = 0.5 + (speed_raw / 100.0) * 4.5
        cycle_len = 1.0 / flash_freq
        cycle_idx = int(t / cycle_len)
        cycle_phase = (t % cycle_len) / cycle_len  # 0.0 to 1.0

        # Update color on new cycle
        if cycle_idx != self.flash_cycle:
            self.flash_cycle = cycle_idx
            if color_mode == "random":
                # Pick vibrant random RGB
                hue = (cycle_idx * 0.381966) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                self.flash_color = (int(r * 255), int(g * 255), int(b * 255))
            elif color_mode == "palette" and palette:
                self.flash_color = palette[cycle_idx % len(palette)]
            else:
                self.flash_color = cfg_color

        # Duty cycle: 50% ON, 50% OFF (square wave)
        is_on = cycle_phase < 0.50
        active_color = self.flash_color if is_on else (0, 0, 0)
        return [active_color] * self.led_count

    def _render_random(self, config: dict, t: float) -> List[Tuple[int, int, int]]:
        """
        Configurable active LED count. Positions and colors remain stable
        until the randomization interval expires, with optional smooth fade.
        """
        count = max(1, min(self.led_count, int(config.get("active_led_count", 20))))
        speed_raw = float(config.get("speed", 35))
        fade = bool(config.get("fade", True))
        color_mode = config.get("color_mode", "random")
        cfg_color = _extract_rgb(config.get("color", DEFAULT_PURPLE))
        palette = [_extract_rgb(c) for c in config.get("palette", DEFAULT_PALETTE)]
        min_b = float(config.get("min_brightness", 0.0))
        max_b = float(config.get("max_brightness", 1.0))

        interval = max(0.2, 2.5 - (speed_raw / 100.0) * 2.1)
        cycle_idx = int(t / interval)
        phase = (t % interval) / interval

        if cycle_idx != self.random_cycle:
            self.random_cycle = cycle_idx
            rng = random.Random(cycle_idx * 7919)
            self.random_positions = rng.sample(range(self.led_count), count)

            new_colors = []
            for i in range(count):
                if color_mode == "single":
                    c = cfg_color
                elif color_mode == "palette" and palette:
                    c = rng.choice(palette)
                else:
                    hue = rng.random()
                    sat = 0.85 + rng.random() * 0.15
                    r, g, b = colorsys.hsv_to_rgb(hue, sat, 1.0)
                    c = (int(r * 255), int(g * 255), int(b * 255))
                new_colors.append(c)

            self.random_prev_colors = list(self.random_colors) if self.random_colors else list(new_colors)
            self.random_colors = new_colors

        frame = [(int(min_b * 255), int(min_b * 255), int(min_b * 255))] * self.led_count

        # Cross-fade factor (e.g. fade in first 35% of interval)
        if fade and phase < 0.35:
            fade_factor = phase / 0.35
        else:
            fade_factor = 1.0

        for idx_in_list, led_pos in enumerate(self.random_positions):
            c_target = self.random_colors[idx_in_list]
            scale = min_b + (max_b - min_b) * fade_factor
            r = int(c_target[0] * scale)
            g = int(c_target[1] * scale)
            b = int(c_target[2] * scale)
            frame[led_pos] = (r, g, b)

        return frame

    def _render_wave(self, config: dict, t: float) -> List[Tuple[int, int, int]]:
        """
        Sinusoidal brightness/color wave travelling across all 300 LEDs.
        """
        color = _extract_rgb(config.get("color", DEFAULT_BLUE))
        bg_color = _extract_rgb(config.get("background_color", {"r": 0, "g": 10, "b": 40}))
        speed_raw = float(config.get("speed", 40))
        width = max(10, float(config.get("width", 60)))
        direction = 1 if config.get("direction", "forward") == "forward" else -1

        freq = 0.2 + (speed_raw / 100.0) * 1.5
        phase_offset = direction * t * freq * 2.0 * math.pi

        frame = []
        for i in range(self.led_count):
            angle = (i / width) * 2.0 * math.pi - phase_offset
            # Wave value in [0, 1]
            w = 0.5 * (1.0 + math.cos(angle))
            r = int(bg_color[0] + (color[0] - bg_color[0]) * w)
            g = int(bg_color[1] + (color[1] - bg_color[1]) * w)
            b = int(bg_color[2] + (color[2] - bg_color[2]) * w)
            frame.append((r, g, b))

        return frame

    def _render_comet(self, config: dict, t: float) -> List[Tuple[int, int, int]]:
        """
        Bright head with exponential decaying tail bouncing across the strip.
        """
        color = _extract_rgb(config.get("color", {"r": 0, "g": 220, "b": 255}))
        speed_raw = float(config.get("speed", 50))
        tail_len = max(5, int(config.get("tail_length", 25)))
        mode = config.get("direction", "bounce")

        leds_per_sec = 20.0 + (speed_raw / 100.0) * 180.0
        max_idx = self.led_count - 1

        if mode == "bounce":
            cycle = 2.0 * max_idx
            dist = (t * leds_per_sec) % cycle
            if dist <= max_idx:
                head = dist
                direction = 1
            else:
                head = max_idx - (dist - max_idx)
                direction = -1
        else:
            direction = 1 if mode == "forward" else -1
            head = (t * leds_per_sec) % self.led_count if direction == 1 else (self.led_count - 1) - (t * leds_per_sec) % self.led_count

        frame = [(0, 0, 0)] * self.led_count
        for k in range(tail_len):
            idx = int(round(head - direction * k))
            if 0 <= idx < self.led_count:
                decay = math.exp(-3.0 * (k / tail_len))
                r = int(color[0] * decay)
                g = int(color[1] * decay)
                b = int(color[2] * decay)
                frame[idx] = (r, g, b)

        return frame

    def _render_breathing(self, config: dict, t: float) -> List[Tuple[int, int, int]]:
        """
        Entire strip smoothly breathes 0% -> 100% -> 0% using sinusoidal easing.
        """
        color = _extract_rgb(config.get("color", {"r": 255, "g": 60, "b": 0}))
        speed_raw = float(config.get("speed", 30))
        min_b = float(config.get("min_brightness", 0.05))
        max_b = float(config.get("max_brightness", 1.0))

        rate = 0.2 + (speed_raw / 100.0) * 1.0
        # Sine ease in [0, 1]
        phase = 0.5 * (1.0 - math.cos(2.0 * math.pi * t * rate))
        scale = min_b + (max_b - min_b) * phase

        r = int(color[0] * scale)
        g = int(color[1] * scale)
        b = int(color[2] * scale)
        return [(r, g, b)] * self.led_count

    def _render_sparkle(self, config: dict, t: float) -> List[Tuple[int, int, int]]:
        """
        Ambient base with stochastic flare-ups decaying over individual lifetimes.
        """
        color = _extract_rgb(config.get("color", DEFAULT_WHITE))
        bg = _extract_rgb(config.get("background_color", {"r": 10, "g": 10, "b": 25}))
        speed_raw = float(config.get("speed", 50))
        decay_rate = float(config.get("decay_rate", 0.15))

        # Decay existing sparkles
        surviving = []
        for sp in self.sparkles:
            sp["life"] -= decay_rate
            if sp["life"] > 0.0:
                surviving.append(sp)
        self.sparkles = surviving

        # Spawn new sparkles based on speed
        spawn_chance = 0.10 + (speed_raw / 100.0) * 0.60
        if random.random() < spawn_chance:
            num_new = random.randint(1, 4)
            for _ in range(num_new):
                pos = random.randint(0, self.led_count - 1)
                self.sparkles.append({"led": pos, "life": 1.0})

        frame = [bg] * self.led_count
        for sp in self.sparkles:
            pos = sp["led"]
            life = sp["life"]
            r = int(bg[0] + (color[0] - bg[0]) * life)
            g = int(bg[1] + (color[1] - bg[1]) * life)
            b = int(bg[2] + (color[2] - bg[2]) * life)
            frame[pos] = (r, g, b)

        return frame

    def _render_color_chase(self, config: dict, t: float) -> List[Tuple[int, int, int]]:
        """
        Multiple colored groups move through the strip with gaps.
        """
        raw_colors = config.get("colors", [DEFAULT_RED, DEFAULT_GREEN, DEFAULT_BLUE, DEFAULT_PURPLE])
        palette = [_extract_rgb(c) for c in raw_colors]
        group_size = max(1, int(config.get("group_size", 15)))
        gap = max(0, int(config.get("gap", 10)))
        speed_raw = float(config.get("speed", 45))
        direction = 1 if config.get("direction", "forward") == "forward" else -1

        leds_per_sec = 15.0 + (speed_raw / 100.0) * 100.0
        unit_len = group_size + gap
        total_cycle = unit_len * len(palette)

        shift = int((direction * t * leds_per_sec) % total_cycle)

        frame = [(0, 0, 0)] * self.led_count
        for i in range(self.led_count):
            pattern_pos = (i - shift) % total_cycle
            group_idx = int(pattern_pos // unit_len)
            offset_in_group = pattern_pos % unit_len

            if offset_in_group < group_size:
                frame[i] = palette[group_idx % len(palette)]
            else:
                frame[i] = (0, 0, 0)

        return frame

    def _render_fire(self, config: dict, t: float) -> List[Tuple[int, int, int]]:
        """
        Procedural warm heat model with cellular cooling, sparking, and smoothing.
        """
        heat_max = float(config.get("heat", 70))
        flicker_rate = float(config.get("flicker", 60)) / 100.0
        speed_raw = float(config.get("speed", 40))

        # Cooling
        cooling = 0.08 + (speed_raw / 100.0) * 0.12
        for i in range(self.led_count):
            self.fire_heat[i] = max(0.0, self.fire_heat[i] - random.uniform(0.0, cooling))

        # Sparking embers at random locations
        num_sparks = int(1 + (flicker_rate * 6))
        for _ in range(num_sparks):
            idx = random.randint(0, self.led_count - 1)
            self.fire_heat[idx] = min(1.0, self.fire_heat[idx] + random.uniform(0.3, 0.7) * (heat_max / 100.0))

        # Cellular diffusion / heat smoothing
        smoothed = np.copy(self.fire_heat)
        for i in range(1, self.led_count - 1):
            smoothed[i] = (self.fire_heat[i - 1] + self.fire_heat[i] * 2.0 + self.fire_heat[i + 1]) / 4.0
        self.fire_heat = smoothed

        # Map heat in [0, 1] to Fire Palette (Black -> Red -> Orange -> Yellow -> White)
        frame = []
        for i in range(self.led_count):
            h = float(self.fire_heat[i])
            if h < 0.33:
                # Black to Red
                frac = h / 0.33
                r = int(frac * 255)
                g = 0
                b = 0
            elif h < 0.66:
                # Red to Orange/Yellow
                frac = (h - 0.33) / 0.33
                r = 255
                g = int(frac * 200)
                b = 0
            else:
                # Yellow to White
                frac = (h - 0.66) / 0.34
                r = 255
                g = 200 + int(frac * 55)
                b = int(frac * 200)
            frame.append((r, g, b))

        return frame

    def _render_rainbow_flow(self, config: dict, t: float) -> List[Tuple[int, int, int]]:
        """
        Continuous travelling HSV rainbow wave across all 300 LEDs.
        """
        speed_raw = float(config.get("speed", 40))
        wavelength = max(20.0, float(config.get("wavelength", 150)))
        sat = float(config.get("saturation", 1.0))
        val = float(config.get("brightness", 1.0))
        direction = 1 if config.get("direction", "forward") == "forward" else -1

        freq = 0.15 + (speed_raw / 100.0) * 0.85
        t_shift = direction * t * freq

        frame = []
        for i in range(self.led_count):
            hue = ((i / wavelength) - t_shift) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
            frame.append((int(r * 255), int(g * 255), int(b * 255)))

        return frame

    # =========================================================================
    # MAIN RENDER ENTRY POINT
    # =========================================================================

    def render(
        self,
        effect_name: str,
        config: dict,
        led_count: int,
        elapsed_time: float,
        dt: float,
        global_brightness: float = 1.0,
        mode_limit: float = 1.0,
        power_on: bool = True,
    ) -> List[Tuple[int, int, int]]:
        """
        Renders a 300-LED frame buffer for the active custom effect, applying
        global user brightness and power gating strictly once.
        """
        if self.led_count != led_count:
            self.led_count = led_count
            self.fire_heat = np.zeros(self.led_count, dtype=np.float32)

        if not power_on:
            return [(0, 0, 0)] * self.led_count

        effect = str(effect_name).lower()
        if effect == "rainfall":
            raw_frame = self._render_rainfall(config, elapsed_time)
        elif effect == "flash":
            raw_frame = self._render_flash(config, elapsed_time)
        elif effect == "random":
            raw_frame = self._render_random(config, elapsed_time)
        elif effect == "wave":
            raw_frame = self._render_wave(config, elapsed_time)
        elif effect == "comet":
            raw_frame = self._render_comet(config, elapsed_time)
        elif effect == "breathing":
            raw_frame = self._render_breathing(config, elapsed_time)
        elif effect == "sparkle":
            raw_frame = self._render_sparkle(config, elapsed_time)
        elif effect == "color_chase":
            raw_frame = self._render_color_chase(config, elapsed_time)
        elif effect == "fire":
            raw_frame = self._render_fire(config, elapsed_time)
        elif effect == "rainbow_flow":
            raw_frame = self._render_rainbow_flow(config, elapsed_time)
        else:
            # Fallback static single-color
            c = _extract_rgb(config.get("color", DEFAULT_WHITE))
            raw_frame = [c] * self.led_count

        # Strictly apply global brightness & mode limit scalar exactly once
        scalar = max(0.0, min(1.0, global_brightness * mode_limit))

        rendered = []
        for r, g, b in raw_frame:
            fr = int(np.clip(round(r * scalar), 0, 255))
            fg = int(np.clip(round(g * scalar), 0, 255))
            fb = int(np.clip(round(b * scalar), 0, 255))
            rendered.append((fr, fg, fb))

        return rendered

    # =========================================================================
    # PROTOCOL V2 ZONE EXTRACTION
    # =========================================================================

    def extract_zones_for_protocol(
        self, frame: List[Tuple[int, int, int]], effect_name: str, config: dict
    ) -> List[dict]:
        """
        Extracts compact hardware zones for Protocol V2 (0x56) transmission.
        Enforces zone count <= 42 for ESP32 UART firmware limits.
        """
        total = len(frame)
        if total == 0:
            return []

        effect = str(effect_name).lower()

        # 1. Single-color uniform effects (1 zone)
        if effect in ("flash", "breathing", "static"):
            first_c = frame[0]
            return [{"start": 0, "end": total - 1, "r": first_c[0], "g": first_c[1], "b": first_c[2]}]

        # 2. Rainfall moving window: emit active LEDs directly
        if effect == "rainfall":
            zones = []
            active_indices = [i for i, c in enumerate(frame) if c != (0, 0, 0)]
            if not active_indices:
                return [{"start": 0, "end": total - 1, "r": 0, "g": 0, "b": 0}]

            min_idx = min(active_indices)
            max_idx = max(active_indices)

            # Leading black region
            if min_idx > 0:
                zones.append({"start": 0, "end": min_idx - 1, "r": 0, "g": 0, "b": 0})

            # Active individual LEDs in trail (up to 30 zones)
            for i in range(min_idx, max_idx + 1):
                c = frame[i]
                zones.append({"start": i, "end": i, "r": c[0], "g": c[1], "b": c[2]})

            # Trailing black region
            if max_idx < total - 1:
                zones.append({"start": max_idx + 1, "end": total - 1, "r": 0, "g": 0, "b": 0})

            if len(zones) <= 42:
                return zones

        # 3. Generic 25-zone chunking for continuous gradient effects
        num_zones = 25
        chunk_size = total / num_zones
        zones = []
        for k in range(num_zones):
            s = int(k * chunk_size)
            e = min(total - 1, int((k + 1) * chunk_size) - 1)
            slice_leds = frame[s : e + 1]
            if slice_leds:
                zr = int(np.mean([c[0] for c in slice_leds]))
                zg = int(np.mean([c[1] for c in slice_leds]))
                zb = int(np.mean([c[2] for c in slice_leds]))
            else:
                zr, zg, zb = 0, 0, 0
            zones.append({"start": s, "end": e, "r": zr, "g": zg, "b": zb})

        return zones
