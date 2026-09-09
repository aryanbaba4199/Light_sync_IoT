from enum import Enum
from dataclasses import dataclass

class EventPriority(Enum):
    AUDIO_BRIGHTNESS = 0
    SCREEN_COLOR = 1
    USER_EFFECT = 2
    DEV_STATUS = 3
    CRITICAL_DEV_EVENT = 4

@dataclass
class LightingState:
    r: int = 0
    g: int = 0
    b: int = 0
    brightness: int = 0 # 0-255 scale
    effect: str = None
    priority: EventPriority = EventPriority.SCREEN_COLOR
    
    def copy_from(self, other):
        self.r = other.r
        self.g = other.g
        self.b = other.b
        self.brightness = other.brightness
        self.effect = other.effect
        self.priority = other.priority

    def validate(self):
        """Ensure all values remain cleanly in 8-bit boundaries to prevent protocol errors."""
        self.r = max(0, min(255, int(self.r)))
        self.g = max(0, min(255, int(self.g)))
        self.b = max(0, min(255, int(self.b)))
        self.brightness = max(0, min(255, int(self.brightness)))
