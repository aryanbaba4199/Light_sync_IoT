"""
Central configuration, models, and validation for Music Mode instrument-to-LED zone mapping.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple
import random
import uuid

# SINGLE SOURCE OF TRUTH FOR LED COUNT
LED_COUNT = 300

class MusicInstrument(str, Enum):
    BASS = "bass"
    KICK = "kick"
    SNARE = "snare"
    VOCAL = "vocal"
    HIHAT = "hihat"
    BRASS = "brass"
    MELODY = "melody"
    BEAT = "beat"
    OVERALL = "overall"

class ResponseEffect(str, Enum):
    STATIC = "static"
    PULSE = "pulse"
    FLASH = "flash"
    SMOOTH = "smooth"

class MusicResponseMode(str, Enum):
    FADE = "fade"
    FLASH = "flash"

class DistributionType(str, Enum):
    ZONE = "zone"
    RANDOM = "random"

@dataclass
class RGBColor:
    r: int = 255
    g: int = 255
    b: int = 255

    def clamp(self):
        self.r = max(0, min(255, int(self.r)))
        self.g = max(0, min(255, int(self.g)))
        self.b = max(0, min(255, int(self.b)))

    def to_dict(self) -> dict:
        return {"r": self.r, "g": self.g, "b": self.b}

    @classmethod
    def from_dict(cls, data: dict) -> 'RGBColor':
        return cls(
            r=max(0, min(255, int(data.get("r", 0)))),
            g=max(0, min(255, int(data.get("g", 0)))),
            b=max(0, min(255, int(data.get("b", 0))))
        )

@dataclass
class MusicMapping:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    instrument: str = MusicInstrument.BASS.value
    color: RGBColor = field(default_factory=lambda: RGBColor(255, 0, 0))
    start_led: int = 1         # 1-based index (1 to LED_COUNT)
    end_led: int = 30          # 1-based index (1 to LED_COUNT)
    sensitivity: float = 1.0   # 0.0 to 2.0 (0% to 200%)
    response: str = ResponseEffect.STATIC.value
    distribution: str = DistributionType.ZONE.value
    enabled: bool = True
    seed: int = 42             # Deterministic seed for random distribution

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "instrument": self.instrument,
            "color": self.color.to_dict() if isinstance(self.color, RGBColor) else self.color,
            "start_led": self.start_led,
            "end_led": self.end_led,
            "sensitivity": round(float(self.sensitivity), 2),
            "response": self.response,
            "distribution": self.distribution,
            "enabled": self.enabled,
            "seed": self.seed
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MusicMapping':
        color_val = data.get("color", {"r": 255, "g": 0, "b": 0})
        color = RGBColor.from_dict(color_val) if isinstance(color_val, dict) else RGBColor()
        return cls(
            id=str(data.get("id", str(uuid.uuid4())[:8])),
            instrument=str(data.get("instrument", MusicInstrument.BASS.value)),
            color=color,
            start_led=int(data.get("start_led", 1)),
            end_led=int(data.get("end_led", 30)),
            sensitivity=float(data.get("sensitivity", 1.0)),
            response=str(data.get("response", ResponseEffect.STATIC.value)),
            distribution=str(data.get("distribution", DistributionType.ZONE.value)),
            enabled=bool(data.get("enabled", True)),
            seed=int(data.get("seed", 42))
        )

@dataclass
class MusicAnalysis:
    bass: float = 0.0
    kick: float = 0.0
    snare: float = 0.0
    vocal: float = 0.0
    hihat: float = 0.0
    brass: float = 0.0
    melody: float = 0.0
    beat: float = 0.0
    overall: float = 0.0
    # Audio Analysis V2 Trigger and Telemetry fields
    kick_trigger: bool = False
    snare_trigger: bool = False
    hihat_trigger: bool = False
    music_gate_open: bool = False
    bass_transient: float = 0.0

    def get_feature(self, instrument: str) -> float:
        val = getattr(self, instrument.lower(), 0.0)
        return max(0.0, min(1.0, float(val)))

    def to_dict(self) -> dict:
        return {
            "bass": round(self.bass, 3),
            "kick": round(self.kick, 3),
            "snare": round(self.snare, 3),
            "vocal": round(self.vocal, 3),
            "hihat": round(self.hihat, 3),
            "brass": round(self.brass, 3),
            "melody": round(self.melody, 3),
            "beat": round(self.beat, 3),
            "overall": round(self.overall, 3),
            "kick_trigger": self.kick_trigger,
            "snare_trigger": self.snare_trigger,
            "hihat_trigger": self.hihat_trigger,
            "music_gate_open": self.music_gate_open,
            "bass_transient": round(self.bass_transient, 3)
        }

def validate_mapping(mapping: MusicMapping, max_leds: int = LED_COUNT) -> Tuple[bool, Optional[str]]:
    """
    Validates a single mapping for logical, range, and type correctness.
    Returns (True, None) if valid, or (False, "Error message") if invalid.
    """
    if mapping.start_led < 1:
        return False, f"Start LED must be >= 1 (got {mapping.start_led})"
    if mapping.end_led > max_leds:
        return False, f"End LED exceeds strip limit of {max_leds} (got {mapping.end_led})"
    if mapping.start_led > mapping.end_led:
        return False, f"Start LED ({mapping.start_led}) must be <= End LED ({mapping.end_led})"
    
    valid_instruments = [i.value for i in MusicInstrument]
    if mapping.instrument not in valid_instruments:
        return False, f"Unknown instrument '{mapping.instrument}'"

    valid_responses = [r.value for r in ResponseEffect]
    if mapping.response not in valid_responses:
        return False, f"Unknown response effect '{mapping.response}'"

    valid_distributions = [d.value for d in DistributionType]
    if mapping.distribution not in valid_distributions:
        return False, f"Unknown distribution '{mapping.distribution}'"

    if mapping.sensitivity < 0.0 or mapping.sensitivity > 5.0:
        return False, f"Sensitivity out of range (got {mapping.sensitivity})"

    return True, None

def check_overlaps(mappings: List[MusicMapping]) -> List[str]:
    """
    Checks for overlapping zones among all enabled mappings.
    Returns a list of human-readable conflict warnings.
    """
    conflicts = []
    enabled = [m for m in mappings if m.enabled]
    
    for i in range(len(enabled)):
        m1 = enabled[i]
        for j in range(i + 1, len(enabled)):
            m2 = enabled[j]
            # Check range overlap: [start1, end1] and [start2, end2]
            if not (m1.end_led < m2.start_led or m1.start_led > m2.end_led):
                conflicts.append(
                    f"{m1.instrument.capitalize()} (LED {m1.start_led}–{m1.end_led}) overlaps with "
                    f"{m2.instrument.capitalize()} (LED {m2.start_led}–{m2.end_led})"
                )
    return conflicts

def generate_deterministic_leds(start_led: int, end_led: int, seed: int) -> List[int]:
    """
    Generates a deterministic list of 0-based LED indices within [start_led - 1, end_led - 1].
    Uses a fixed random seed so that assignments remain completely stable across frames
    and only reshuffle when the configuration or seed explicitly changes.
    """
    rng = random.Random(seed)
    indices = list(range(start_led - 1, end_led))
    rng.shuffle(indices)
    return indices

# PRESETS (Editable, fully populated defaults)
DEFAULT_3_BAND_PRESET: List[dict] = [
    {
        "id": "preset_3b_1",
        "instrument": "bass",
        "color": {"r": 255, "g": 0, "b": 0},
        "start_led": 1,
        "end_led": 100,
        "sensitivity": 1.0,
        "response": "static",
        "distribution": "zone",
        "enabled": True,
        "seed": 101
    },
    {
        "id": "preset_3b_2",
        "instrument": "vocal",
        "color": {"r": 0, "g": 255, "b": 0},
        "start_led": 101,
        "end_led": 200,
        "sensitivity": 1.0,
        "response": "static",
        "distribution": "zone",
        "enabled": True,
        "seed": 102
    },
    {
        "id": "preset_3b_3",
        "instrument": "hihat",
        "color": {"r": 0, "g": 0, "b": 255},
        "start_led": 201,
        "end_led": 300,
        "sensitivity": 1.0,
        "response": "static",
        "distribution": "zone",
        "enabled": True,
        "seed": 103
    }
]

PARTY_PRESET: List[dict] = [
    {
        "id": "party_1",
        "instrument": "bass",
        "color": {"r": 255, "g": 0, "b": 50},
        "start_led": 1,
        "end_led": 40,
        "sensitivity": 1.2,
        "response": "pulse",
        "distribution": "zone",
        "enabled": True,
        "seed": 201
    },
    {
        "id": "party_2",
        "instrument": "kick",
        "color": {"r": 255, "g": 100, "b": 0},
        "start_led": 41,
        "end_led": 80,
        "sensitivity": 1.3,
        "response": "flash",
        "distribution": "zone",
        "enabled": True,
        "seed": 202
    },
    {
        "id": "party_3",
        "instrument": "snare",
        "color": {"r": 255, "g": 220, "b": 0},
        "start_led": 81,
        "end_led": 130,
        "sensitivity": 1.1,
        "response": "flash",
        "distribution": "zone",
        "enabled": True,
        "seed": 203
    },
    {
        "id": "party_4",
        "instrument": "vocal",
        "color": {"r": 180, "g": 0, "b": 255},
        "start_led": 131,
        "end_led": 190,
        "sensitivity": 1.0,
        "response": "smooth",
        "distribution": "zone",
        "enabled": True,
        "seed": 204
    },
    {
        "id": "party_5",
        "instrument": "hihat",
        "color": {"r": 0, "g": 220, "b": 255},
        "start_led": 191,
        "end_led": 240,
        "sensitivity": 1.0,
        "response": "pulse",
        "distribution": "zone",
        "enabled": True,
        "seed": 205
    },
    {
        "id": "party_6",
        "instrument": "melody",
        "color": {"r": 0, "g": 255, "b": 100},
        "start_led": 241,
        "end_led": 300,
        "sensitivity": 1.0,
        "response": "smooth",
        "distribution": "zone",
        "enabled": True,
        "seed": 206
    }
]

FULL_BAND_PRESET: List[dict] = [
    {
        "id": "band_1",
        "instrument": "bass",
        "color": {"r": 255, "g": 0, "b": 0},
        "start_led": 1,
        "end_led": 35,
        "sensitivity": 1.1,
        "response": "pulse",
        "distribution": "zone",
        "enabled": True,
        "seed": 301
    },
    {
        "id": "band_2",
        "instrument": "kick",
        "color": {"r": 255, "g": 90, "b": 0},
        "start_led": 36,
        "end_led": 70,
        "sensitivity": 1.2,
        "response": "flash",
        "distribution": "zone",
        "enabled": True,
        "seed": 302
    },
    {
        "id": "band_3",
        "instrument": "snare",
        "color": {"r": 255, "g": 200, "b": 0},
        "start_led": 71,
        "end_led": 110,
        "sensitivity": 1.1,
        "response": "flash",
        "distribution": "zone",
        "enabled": True,
        "seed": 303
    },
    {
        "id": "band_4",
        "instrument": "vocal",
        "color": {"r": 160, "g": 0, "b": 255},
        "start_led": 111,
        "end_led": 160,
        "sensitivity": 1.0,
        "response": "smooth",
        "distribution": "zone",
        "enabled": True,
        "seed": 304
    },
    {
        "id": "band_5",
        "instrument": "hihat",
        "color": {"r": 0, "g": 200, "b": 255},
        "start_led": 161,
        "end_led": 200,
        "sensitivity": 1.0,
        "response": "pulse",
        "distribution": "zone",
        "enabled": True,
        "seed": 305
    },
    {
        "id": "band_6",
        "instrument": "brass",
        "color": {"r": 255, "g": 160, "b": 20},
        "start_led": 201,
        "end_led": 245,
        "sensitivity": 1.0,
        "response": "pulse",
        "distribution": "zone",
        "enabled": True,
        "seed": 306
    },
    {
        "id": "band_7",
        "instrument": "melody",
        "color": {"r": 0, "g": 255, "b": 120},
        "start_led": 246,
        "end_led": 300,
        "sensitivity": 1.0,
        "response": "smooth",
        "distribution": "zone",
        "enabled": True,
        "seed": 307
    }
]

PRESETS: Dict[str, List[dict]] = {
    "default_3_band": DEFAULT_3_BAND_PRESET,
    "party": PARTY_PRESET,
    "full_band": FULL_BAND_PRESET
}
