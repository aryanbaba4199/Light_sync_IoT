"""
MusicMappingEngine: Converts real audio feature analysis and user mappings
into a 300-LED physical frame buffer.
"""
from typing import List, Dict, Tuple, Optional
import time
from music_models import (
    LED_COUNT,
    MusicAnalysis,
    MusicMapping,
    ResponseEffect,
    DistributionType,
    generate_deterministic_leds
)

# Reusable effect processor with stateful envelope memory per mapping
class ResponseEffectProcessor:
    def __init__(self):
        # Memory keyed by mapping ID
        self.envelopes: Dict[str, float] = {}
        self.last_update_time: Dict[str, float] = {}

    def process(self, mapping_id: str, effect: str, raw_intensity: float) -> float:
        now = time.time()
        prev = self.envelopes.get(mapping_id, 0.0)
        dt = min(0.1, max(0.001, now - self.last_update_time.get(mapping_id, now)))
        self.last_update_time[mapping_id] = now

        if effect == ResponseEffect.STATIC.value:
            # Follows intensity directly
            envelope = raw_intensity

        elif effect == ResponseEffect.PULSE.value:
            # Smooth musical attack / release curve
            if raw_intensity > prev:
                # Fast attack
                envelope = prev + (raw_intensity - prev) * min(1.0, dt * 15.0)
            else:
                # Slower release
                envelope = prev - (prev - raw_intensity) * min(1.0, dt * 4.0)

        elif effect == ResponseEffect.FLASH.value:
            # Instantaneous spike on transients, rapid exponential decay
            if raw_intensity > prev:
                envelope = raw_intensity
            else:
                envelope = prev * max(0.0, 1.0 - (dt * 12.0))

        elif effect == ResponseEffect.SMOOTH.value:
            # Slow ambient transition
            rate = min(1.0, dt * 3.0)
            envelope = prev * (1.0 - rate) + raw_intensity * rate

        else:
            envelope = raw_intensity

        clamped = max(0.0, min(1.0, envelope))
        self.envelopes[mapping_id] = clamped
        return clamped

class FlashEventManager:
    """
    Manages binary FLASH event triggers, hold durations, and refractory cooldowns per mapping.
    Ensures that in FLASH mode, mapped zones are strictly 0.0 (OFF) or 1.0 (FULL BRIGHTNESS),
    scaled solely by global brightness and mode limits (no intermediate brightness).
    """
    def __init__(self):
        # mapping_id -> timestamp until which flash is active
        self.flash_until: Dict[str, float] = {}
        # mapping_id -> timestamp when next flash trigger is permitted
        self.cooldown_until: Dict[str, float] = {}
        # mapping_id -> previous feature value for onset detection
        self.prev_feature: Dict[str, float] = {}

    def get_flash_timing(self, instrument: str) -> Tuple[float, float]:
        """Returns (duration_sec, cooldown_sec) for the given instrument."""
        inst = instrument.lower()
        if inst == "hihat":
            return (0.045, 0.050)  # Very short, crisp 45ms flash, 50ms cooldown
        elif inst == "snare":
            return (0.075, 0.085)  # Fast 75ms flash, 85ms cooldown
        elif inst == "kick":
            return (0.085, 0.095)  # Strong, punchy 85ms flash, 95ms cooldown
        elif inst == "bass":
            return (0.085, 0.095)  # 85ms flash on bass onset, 95ms cooldown
        else:
            return (0.080, 0.090)  # 80ms flash for vocal/melody/others, 90ms cooldown

    def is_flash_active(
        self,
        mapping_id: str,
        instrument: str,
        sensitivity: float,
        analysis: MusicAnalysis,
        now: float
    ) -> bool:
        """
        Evaluates whether a mapping is currently flashing (1.0) or off (0.0).
        Strictly binary output.
        """
        # 1. Master activity gate check (ambient room/fan noise/silence -> strictly OFF)
        if not analysis.music_gate_open:
            self.flash_until[mapping_id] = 0.0
            return False

        # 2. Check if an active flash is currently holding
        if now < self.flash_until.get(mapping_id, 0.0):
            return True

        # 3. Check refractory cooldown
        if now < self.cooldown_until.get(mapping_id, 0.0):
            return False

        # 4. Detect whether a new meaningful musical event occurred
        s = max(0.1, float(sensitivity))
        inst = instrument.lower()
        triggered = False

        if inst == "kick":
            if analysis.kick_trigger or analysis.kick >= max(0.20, 0.45 / s):
                triggered = True

        elif inst == "snare":
            if analysis.snare_trigger or analysis.snare >= max(0.20, 0.40 / s):
                triggered = True

        elif inst == "hihat":
            if analysis.hihat_trigger or analysis.hihat >= max(0.15, 0.35 / s):
                triggered = True

        elif inst == "bass":
            # In FLASH mode: ONLY trigger on bass transient onsets / attacks!
            # Do NOT keep Bass permanently at 100% merely because low-frequency energy is sustained.
            bass_trans = getattr(analysis, "bass_transient", 0.0)
            prev_b = self.prev_feature.get(mapping_id, 0.0)
            rise = max(0.0, analysis.bass - prev_b)
            if bass_trans >= max(0.20, 0.45 / s) or (rise >= max(0.15, 0.30 / s) and analysis.bass >= 0.25):
                triggered = True
            self.prev_feature[mapping_id] = analysis.bass

        elif inst == "vocal":
            prev_v = self.prev_feature.get(mapping_id, 0.0)
            rise = max(0.0, analysis.vocal - prev_v)
            if analysis.vocal >= max(0.20, 0.40 / s) and (rise >= 0.15 or analysis.vocal >= 0.65):
                triggered = True
            self.prev_feature[mapping_id] = analysis.vocal

        elif inst == "melody":
            prev_m = self.prev_feature.get(mapping_id, 0.0)
            rise = max(0.0, analysis.melody - prev_m)
            if analysis.melody >= max(0.20, 0.35 / s) and (rise >= 0.15 or analysis.melody >= 0.60):
                triggered = True
            self.prev_feature[mapping_id] = analysis.melody

        elif inst == "beat":
            if analysis.beat >= max(0.20, 0.40 / s):
                triggered = True

        elif inst == "overall":
            if analysis.overall >= max(0.25, 0.50 / s):
                triggered = True

        else:
            feat = analysis.get_feature(inst)
            prev_f = self.prev_feature.get(mapping_id, 0.0)
            rise = max(0.0, feat - prev_f)
            if feat >= max(0.20, 0.40 / s) and rise >= 0.15:
                triggered = True
            self.prev_feature[mapping_id] = feat

        if triggered:
            duration, cooldown = self.get_flash_timing(inst)
            self.flash_until[mapping_id] = now + duration
            self.cooldown_until[mapping_id] = now + cooldown
            return True

        return False

    def clear(self):
        self.flash_until.clear()
        self.cooldown_until.clear()
        self.prev_feature.clear()

class MusicMappingEngine:
    def __init__(self, led_count: int = LED_COUNT):
        self.led_count = led_count
        self.effect_processor = ResponseEffectProcessor()
        self.flash_manager = FlashEventManager()
        # Cache for deterministic random indices: (mapping_id, seed, start_led, end_led) -> list
        self._random_cache: Dict[Tuple[str, int, int, int], List[int]] = {}

    def _get_random_indices(self, mapping: MusicMapping) -> List[int]:
        key = (mapping.id, mapping.seed, mapping.start_led, mapping.end_led)
        if key not in self._random_cache:
            indices = generate_deterministic_leds(mapping.start_led, mapping.end_led, mapping.seed)
            self._random_cache[key] = indices
        return self._random_cache[key]

    def render_frame(
        self,
        analysis: MusicAnalysis,
        mappings: List[MusicMapping],
        user_brightness: float = 1.0,
        mode_limit: float = 1.0,
        power_on: bool = True,
        response_mode: str = "fade"
    ) -> List[Tuple[int, int, int]]:
        """
        Renders a complete frame buffer of length `self.led_count`.
        Each element is an (R, G, B) tuple in 0–255 range.

        Response Modes:
        - FLASH (Default): Strictly binary (0.0 or 1.0) output scaled by master brightness.
          No intermediate brightness levels. Uses transient/onset event detection with refractory timing.
        - FADE: Continuous fluid brightness following audio feature curves.
        """
        # 1. Global power check
        if not power_on:
            return [(0, 0, 0)] * self.led_count

        # Initialize black frame buffer
        frame = [[0, 0, 0] for _ in range(self.led_count)]

        # Clamped master brightness multiplier (0.0 to 1.0)
        master_mult = max(0.0, min(1.0, user_brightness)) * max(0.0, min(1.0, mode_limit))
        now = time.time()
        is_flash_mode = (str(response_mode).lower() == "flash")

        for mapping in mappings:
            if not mapping.enabled:
                continue

            # Validate range bounds
            s = max(1, min(self.led_count, mapping.start_led))
            e = max(1, min(self.led_count, mapping.end_led))
            if s > e:
                continue

            if is_flash_mode:
                # FLASH MODE: Strictly binary 0.0 or 1.0 (NO intermediate brightness)
                is_active = self.flash_manager.is_flash_active(
                    mapping.id, mapping.instrument, mapping.sensitivity, analysis, now
                )
                applied_intensity = 1.0 if is_active else 0.0
            else:
                # FADE MODE: Fluid, continuous intensity following audio feature
                if mapping.instrument == "bass" and mapping.response == "flash":
                    feat_val = getattr(analysis, "bass_transient", 0.0)
                else:
                    feat_val = analysis.get_feature(mapping.instrument)
                raw_intensity = max(0.0, min(1.0, feat_val * mapping.sensitivity))
                applied_intensity = self.effect_processor.process(mapping.id, mapping.response, raw_intensity)

            # Master brightness applied exactly once
            final_intensity = applied_intensity * master_mult

            # Calculate color components
            cr = max(0, min(255, int(mapping.color.r * final_intensity)))
            cg = max(0, min(255, int(mapping.color.g * final_intensity)))
            cb = max(0, min(255, int(mapping.color.b * final_intensity)))

            if cr == 0 and cg == 0 and cb == 0:
                continue

            # Apply to LEDs based on distribution
            if mapping.distribution == DistributionType.RANDOM.value:
                assigned_leds = self._get_random_indices(mapping)
                for led_idx in assigned_leds:
                    if 0 <= led_idx < self.led_count:
                        frame[led_idx][0] = min(255, frame[led_idx][0] + cr)
                        frame[led_idx][1] = min(255, frame[led_idx][1] + cg)
                        frame[led_idx][2] = min(255, frame[led_idx][2] + cb)
            else:
                for led_idx in range(s - 1, e):
                    frame[led_idx][0] = min(255, frame[led_idx][0] + cr)
                    frame[led_idx][1] = min(255, frame[led_idx][1] + cg)
                    frame[led_idx][2] = min(255, frame[led_idx][2] + cb)

        return [(r, g, b) for r, g, b in frame]

    def extract_zones_for_protocol(
        self,
        analysis: MusicAnalysis,
        mappings: List[MusicMapping],
        user_brightness: float = 1.0,
        mode_limit: float = 1.0,
        power_on: bool = True,
        response_mode: str = "fade"
    ) -> List[dict]:
        """
        Extracts active zones with their calculated RGB for lightweight Protocol V2 transmission.
        Returns a list of dicts: [{'start': 0, 'end': 29, 'r': 255, 'g': 0, 'b': 0}, ...]
        """
        if not power_on:
            return []

        master_mult = max(0.0, min(1.0, user_brightness)) * max(0.0, min(1.0, mode_limit))
        now = time.time()
        is_flash_mode = (str(response_mode).lower() == "flash")
        zones = []

        for mapping in mappings:
            if not mapping.enabled:
                continue
            s = max(1, min(self.led_count, mapping.start_led))
            e = max(1, min(self.led_count, mapping.end_led))
            if s > e:
                continue

            if is_flash_mode:
                # FLASH MODE: Strictly binary 0.0 or 1.0
                is_active = self.flash_manager.is_flash_active(
                    mapping.id, mapping.instrument, mapping.sensitivity, analysis, now
                )
                applied_intensity = 1.0 if is_active else 0.0
            else:
                # FADE MODE: Fluid continuous intensity
                if mapping.instrument == "bass" and mapping.response == "flash":
                    feat_val = getattr(analysis, "bass_transient", 0.0)
                else:
                    feat_val = analysis.get_feature(mapping.instrument)
                raw_intensity = max(0.0, min(1.0, feat_val * mapping.sensitivity))
                applied_intensity = self.effect_processor.process(mapping.id, mapping.response, raw_intensity)

            final_intensity = applied_intensity * master_mult

            cr = max(0, min(255, int(mapping.color.r * final_intensity)))
            cg = max(0, min(255, int(mapping.color.g * final_intensity)))
            cb = max(0, min(255, int(mapping.color.b * final_intensity)))

            zones.append({
                "id": mapping.id,
                "start": s - 1,  # 0-based
                "end": e - 1,    # 0-based
                "r": cr,
                "g": cg,
                "b": cb,
                "distribution": mapping.distribution,
                "seed": mapping.seed
            })

        return zones
