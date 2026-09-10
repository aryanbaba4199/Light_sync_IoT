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

    def clear(self):
        self.envelopes.clear()
        self.last_update_time.clear()

class MusicMappingEngine:
    def __init__(self, led_count: int = LED_COUNT):
        self.led_count = led_count
        self.effect_processor = ResponseEffectProcessor()
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
        power_on: bool = True
    ) -> List[Tuple[int, int, int]]:
        """
        Renders a complete frame buffer of length `self.led_count`.
        Each element is an (R, G, B) tuple in 0–255 range.

        Brightness flow:
        1. Power check: If power_on is False, returns all (0, 0, 0).
        2. Feature intensity: feature = analysis.get_feature(instrument).
        3. Sensitivity: raw_intensity = clamp(feature * sensitivity, 0.0, 1.0).
        4. Response effect: applied intensity = effect_processor.process(effect, raw_intensity).
        5. Master brightness multiplier: master_mult = user_brightness * mode_limit (applied exactly ONCE).
        6. Per-LED RGB = (R * final_intensity, G * final_intensity, B * final_intensity).
        """
        # 1. Global power check
        if not power_on:
            return [(0, 0, 0)] * self.led_count

        # Initialize black frame buffer
        frame = [[0, 0, 0] for _ in range(self.led_count)]

        # Clamped master brightness multiplier (0.0 to 1.0)
        master_mult = max(0.0, min(1.0, user_brightness)) * max(0.0, min(1.0, mode_limit))

        for mapping in mappings:
            if not mapping.enabled:
                continue

            # Validate range bounds
            s = max(1, min(self.led_count, mapping.start_led))
            e = max(1, min(self.led_count, mapping.end_led))
            if s > e:
                continue

            # 2. Extract feature
            feat_val = analysis.get_feature(mapping.instrument)

            # 3. Apply sensitivity
            raw_intensity = max(0.0, min(1.0, feat_val * mapping.sensitivity))

            # 4. Apply response effect
            processed_intensity = self.effect_processor.process(mapping.id, mapping.response, raw_intensity)

            # 5. Master brightness applied exactly once
            final_intensity = processed_intensity * master_mult

            # Calculate color components
            cr = max(0, min(255, int(mapping.color.r * final_intensity)))
            cg = max(0, min(255, int(mapping.color.g * final_intensity)))
            cb = max(0, min(255, int(mapping.color.b * final_intensity)))

            # 6. Apply to LEDs based on distribution
            if mapping.distribution == DistributionType.RANDOM.value:
                assigned_leds = self._get_random_indices(mapping)
                for led_idx in assigned_leds:
                    if 0 <= led_idx < self.led_count:
                        # Zone blending if multiple mappings share an LED
                        frame[led_idx][0] = min(255, frame[led_idx][0] + cr)
                        frame[led_idx][1] = min(255, frame[led_idx][1] + cg)
                        frame[led_idx][2] = min(255, frame[led_idx][2] + cb)
            else:
                # Contiguous zone (0-based indexing)
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
        power_on: bool = True
    ) -> List[dict]:
        """
        Extracts active zones with their calculated RGB for lightweight Protocol V2 transmission.
        Returns a list of dicts: [{'start': 0, 'end': 29, 'r': 255, 'g': 0, 'b': 0}, ...]
        """
        if not power_on:
            return []

        master_mult = max(0.0, min(1.0, user_brightness)) * max(0.0, min(1.0, mode_limit))
        zones = []

        for mapping in mappings:
            if not mapping.enabled:
                continue
            s = max(1, min(self.led_count, mapping.start_led))
            e = max(1, min(self.led_count, mapping.end_led))
            if s > e:
                continue

            feat_val = analysis.get_feature(mapping.instrument)
            raw_intensity = max(0.0, min(1.0, feat_val * mapping.sensitivity))
            processed_intensity = self.effect_processor.process(mapping.id, mapping.response, raw_intensity)
            final_intensity = processed_intensity * master_mult

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
