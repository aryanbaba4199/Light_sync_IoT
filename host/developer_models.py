import time
from enum import Enum, IntEnum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

class DeveloperEventType(str, Enum):
    # Coding
    CODE_ACTIVE = "CODE_ACTIVE"
    CODING_ACTIVITY = "CODING_ACTIVITY"
    FILE_SAVED = "FILE_SAVED"
    CODE_WARNING = "CODE_WARNING"
    CODE_ERROR = "CODE_ERROR"

    # Build
    BUILD_STARTED = "BUILD_STARTED"
    BUILD_SUCCESS = "BUILD_SUCCESS"
    BUILD_FAILED = "BUILD_FAILED"

    # Tests
    TEST_STARTED = "TEST_STARTED"
    TEST_SUCCESS = "TEST_SUCCESS"
    TEST_FAILED = "TEST_FAILED"

    # Git
    GIT_COMMIT = "GIT_COMMIT"
    GIT_PUSH = "GIT_PUSH"
    PR_CREATED = "PR_CREATED"
    PR_MERGED = "PR_MERGED"

    # Deployment
    DEPLOY_STARTED = "DEPLOY_STARTED"
    DEPLOY_SUCCESS = "DEPLOY_SUCCESS"
    DEPLOY_FAILED = "DEPLOY_FAILED"

    # Runtime
    SERVER_STARTED = "SERVER_STARTED"
    SERVER_STOPPED = "SERVER_STOPPED"
    SERVER_ERROR = "SERVER_ERROR"

    # General
    WARNING = "WARNING"
    ERROR = "ERROR"

    @classmethod
    def has_value(cls, value: str) -> bool:
        return any(item.value == value for item in cls)

    @classmethod
    def from_string(cls, name: str) -> Optional["DeveloperEventType"]:
        try:
            return cls(name.strip().upper())
        except (ValueError, KeyError, AttributeError):
            return None


class DeveloperState(str, Enum):
    IDLE = "IDLE"
    CODING = "CODING"
    BUILDING = "BUILDING"
    TESTING = "TESTING"
    DEPLOYING = "DEPLOYING"


class DeveloperPriority(IntEnum):
    LOW = 1
    STATUS = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5


@dataclass
class DeveloperZone:
    """
    Represents an LED zone for developer visualization.
    start_led and end_led are 1-based (inclusive) for user configuration and UI.
    start_idx and end_idx are 0-based (inclusive) for internal array indexing.
    """
    name: str
    start_led: int  # 1-based inclusive
    end_led: int    # 1-based inclusive

    @property
    def start_idx(self) -> int:
        return self.start_led - 1

    @property
    def end_idx(self) -> int:
        return self.end_led - 1

    @property
    def led_count(self) -> int:
        return max(0, self.end_led - self.start_led + 1)

    def validate(self, total_leds: int = 300) -> Tuple[bool, Optional[str]]:
        if self.start_led < 1:
            return False, f"Zone '{self.name}' start_led ({self.start_led}) must be >= 1"
        if self.end_led < self.start_led:
            return False, f"Zone '{self.name}' end_led ({self.end_led}) must be >= start_led ({self.start_led})"
        if self.end_led > total_leds:
            return False, f"Zone '{self.name}' end_led ({self.end_led}) exceeds total LEDs ({total_leds})"
        return True, None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start_led": self.start_led,
            "end_led": self.end_led
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeveloperZone":
        return cls(
            name=str(data.get("name", "")),
            start_led=int(data.get("start_led", 1)),
            end_led=int(data.get("end_led", 1))
        )


@dataclass
class DeveloperLayout:
    zones: Dict[str, DeveloperZone] = field(default_factory=dict)
    total_leds: int = 300

    @classmethod
    def default(cls, total_leds: int = 300) -> "DeveloperLayout":
        """
        Default logical layout:
        BUILD: LED 1–75
        TEST: LED 76–150
        GIT: LED 151–225
        DEPLOY: LED 226–300
        """
        return cls(
            zones={
                "build": DeveloperZone(name="build", start_led=1, end_led=75),
                "test": DeveloperZone(name="test", start_led=76, end_led=150),
                "git": DeveloperZone(name="git", start_led=151, end_led=225),
                "deploy": DeveloperZone(name="deploy", start_led=226, end_led=300),
            },
            total_leds=total_leds
        )

    def validate(self) -> Tuple[bool, Optional[str]]:
        for name, zone in self.zones.items():
            valid, err = zone.validate(self.total_leds)
            if not valid:
                return False, err
        return True, None

    def to_dict(self) -> dict:
        return {name: zone.to_dict() for name, zone in self.zones.items()}

    @classmethod
    def from_dict(cls, data: dict, total_leds: int = 300) -> "DeveloperLayout":
        zones = {}
        for name, z_data in data.items():
            if isinstance(z_data, dict):
                z_copy = dict(z_data)
                z_copy.setdefault("name", name)
                zones[name] = DeveloperZone.from_dict(z_copy)
        if not zones:
            return cls.default(total_leds)
        return cls(zones=zones, total_leds=total_leds)


@dataclass
class DeveloperEvent:
    event_type: DeveloperEventType
    priority: DeveloperPriority = DeveloperPriority.STATUS
    duration: float = 3.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def expiration(self) -> float:
        return self.timestamp + self.duration

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        t = current_time if current_time is not None else time.time()
        return t >= self.expiration

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value if hasattr(self.event_type, "value") else str(self.event_type),
            "priority": int(self.priority),
            "duration": self.duration,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


# Standard profiles for event prioritization and duration defaults
EVENT_PROFILES: Dict[DeveloperEventType, Tuple[DeveloperPriority, float, Optional[str]]] = {
    # Coding
    DeveloperEventType.CODE_ACTIVE: (DeveloperPriority.LOW, 2.0, None),
    DeveloperEventType.CODING_ACTIVITY: (DeveloperPriority.LOW, 2.0, None),
    DeveloperEventType.FILE_SAVED: (DeveloperPriority.STATUS, 2.0, "git"),
    DeveloperEventType.CODE_WARNING: (DeveloperPriority.WARNING, 3.0, None),
    DeveloperEventType.CODE_ERROR: (DeveloperPriority.ERROR, 4.0, None),

    # Build
    DeveloperEventType.BUILD_STARTED: (DeveloperPriority.STATUS, 3.0, "build"),
    DeveloperEventType.BUILD_SUCCESS: (DeveloperPriority.STATUS, 3.0, "build"),
    DeveloperEventType.BUILD_FAILED: (DeveloperPriority.CRITICAL, 5.0, "build"),

    # Tests
    DeveloperEventType.TEST_STARTED: (DeveloperPriority.STATUS, 3.0, "test"),
    DeveloperEventType.TEST_SUCCESS: (DeveloperPriority.STATUS, 3.0, "test"),
    DeveloperEventType.TEST_FAILED: (DeveloperPriority.CRITICAL, 5.0, "test"),

    # Git
    DeveloperEventType.GIT_COMMIT: (DeveloperPriority.STATUS, 2.5, "git"),
    DeveloperEventType.GIT_PUSH: (DeveloperPriority.STATUS, 2.5, "git"),
    DeveloperEventType.PR_CREATED: (DeveloperPriority.STATUS, 3.0, "git"),
    DeveloperEventType.PR_MERGED: (DeveloperPriority.STATUS, 3.5, "git"),

    # Deployment
    DeveloperEventType.DEPLOY_STARTED: (DeveloperPriority.STATUS, 3.0, "deploy"),
    DeveloperEventType.DEPLOY_SUCCESS: (DeveloperPriority.STATUS, 3.0, "deploy"),
    DeveloperEventType.DEPLOY_FAILED: (DeveloperPriority.CRITICAL, 5.0, "deploy"),

    # Runtime
    DeveloperEventType.SERVER_STARTED: (DeveloperPriority.STATUS, 3.0, None),
    DeveloperEventType.SERVER_STOPPED: (DeveloperPriority.WARNING, 3.0, None),
    DeveloperEventType.SERVER_ERROR: (DeveloperPriority.CRITICAL, 5.0, None),

    # General
    DeveloperEventType.WARNING: (DeveloperPriority.WARNING, 3.0, None),
    DeveloperEventType.ERROR: (DeveloperPriority.CRITICAL, 5.0, None),
}

def get_event_profile(event_type: DeveloperEventType) -> Tuple[DeveloperPriority, float, Optional[str]]:
    return EVENT_PROFILES.get(event_type, (DeveloperPriority.STATUS, 3.0, None))
