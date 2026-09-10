"""
Movie Mode Data Models and Configuration for DevLights.

Supports rectangular/square perimeter configurations for ambient TV/monitor backlighting.
Default:
  - Top: 100 LEDs
  - Right: 50 LEDs
  - Bottom: 100 LEDs
  - Left: 50 LEDs
  Total: 300 LEDs
"""
from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any, List

DEFAULT_TOP_LEDS = 100
DEFAULT_RIGHT_LEDS = 50
DEFAULT_BOTTOM_LEDS = 100
DEFAULT_LEFT_LEDS = 50
DEFAULT_TOTAL_LEDS = 300
DEFAULT_SAMPLING_THICKNESS = 0.10  # 10% inward from active video boundary


@dataclass
class MovieLayout:
    top: int = DEFAULT_TOP_LEDS
    right: int = DEFAULT_RIGHT_LEDS
    bottom: int = DEFAULT_BOTTOM_LEDS
    left: int = DEFAULT_LEFT_LEDS
    sampling_thickness: float = DEFAULT_SAMPLING_THICKNESS
    clockwise: bool = True  # Clockwise: Top (L->R), Right (T->B), Bottom (R->L), Left (B->T)

    @property
    def total_leds(self) -> int:
        return self.top + self.right + self.bottom + self.left

    def validate(self, max_leds: int = DEFAULT_TOTAL_LEDS) -> Tuple[bool, Optional[str]]:
        if self.top < 0 or self.right < 0 or self.bottom < 0 or self.left < 0:
            return False, "Bulb counts cannot be negative"
        if self.total_leds == 0:
            return False, "Total bulb count must be greater than 0"
        if self.total_leds > max_leds * 2:
            return False, f"Total bulb count ({self.total_leds}) exceeds maximum supported ({max_leds * 2})"
        if not (0.02 <= self.sampling_thickness <= 0.40):
            return False, "Sampling thickness must be between 0.02 (2%) and 0.40 (40%)"
        return True, None

    def get_edge_ranges(self) -> Dict[str, Tuple[int, int]]:
        """
        Returns 0-based index ranges [start, end) for each edge in physical continuous order.
        Clockwise default:
          Top: [0, top)
          Right: [top, top + right)
          Bottom: [top + right, top + right + bottom)
          Left: [top + right + bottom, total)
        """
        if self.clockwise:
            top_start = 0
            top_end = self.top
            right_start = top_end
            right_end = right_start + self.right
            bottom_start = right_end
            bottom_end = bottom_start + self.bottom
            left_start = bottom_end
            left_end = left_start + self.left
            return {
                "top": (top_start, top_end),
                "right": (right_start, right_end),
                "bottom": (bottom_start, bottom_end),
                "left": (left_start, left_end),
            }
        else:
            # Counter-clockwise: Top (R->L), Left (T->B), Bottom (L->R), Right (B->T)
            top_start = 0
            top_end = self.top
            left_start = top_end
            left_end = left_start + self.left
            bottom_start = left_end
            bottom_end = bottom_start + self.bottom
            right_start = bottom_end
            right_end = right_start + self.right
            return {
                "top": (top_start, top_end),
                "left": (left_start, left_end),
                "bottom": (bottom_start, bottom_end),
                "right": (right_start, right_end),
            }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
            "left": self.left,
            "sampling_thickness": round(self.sampling_thickness, 3),
            "clockwise": self.clockwise,
            "total_leds": self.total_leds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MovieLayout":
        return cls(
            top=int(data.get("top", DEFAULT_TOP_LEDS)),
            right=int(data.get("right", DEFAULT_RIGHT_LEDS)),
            bottom=int(data.get("bottom", DEFAULT_BOTTOM_LEDS)),
            left=int(data.get("left", DEFAULT_LEFT_LEDS)),
            sampling_thickness=float(data.get("sampling_thickness", DEFAULT_SAMPLING_THICKNESS)),
            clockwise=bool(data.get("clockwise", True)),
        )


@dataclass
class MovieSettings:
    layout: MovieLayout = field(default_factory=MovieLayout)
    monitor_index: int = 1  # Display index (1, 2, 3...)
    sync_music: bool = False
    smoothing: float = 0.70
    brightness_limit: float = 1.0
    min_music_brightness: float = 0.35  # Quiet floor when music sync is ON
    max_music_brightness: float = 1.00  # Loud peak when music sync is ON

    def to_dict(self) -> Dict[str, Any]:
        return {
            "top": self.layout.top,
            "right": self.layout.right,
            "bottom": self.layout.bottom,
            "left": self.layout.left,
            "sampling_thickness": self.layout.sampling_thickness,
            "clockwise": self.layout.clockwise,
            "monitor_index": self.monitor_index,
            "sync_music": self.sync_music,
            "smoothing": self.smoothing,
            "brightness_limit": self.brightness_limit,
            "min_music_brightness": self.min_music_brightness,
            "max_music_brightness": self.max_music_brightness,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MovieSettings":
        layout = MovieLayout.from_dict(data)
        return cls(
            layout=layout,
            monitor_index=int(data.get("monitor_index", 1)),
            sync_music=bool(data.get("sync_music", False)),
            smoothing=float(data.get("smoothing", 0.70)),
            brightness_limit=float(data.get("brightness_limit", 1.0)),
            min_music_brightness=float(data.get("min_music_brightness", 0.35)),
            max_music_brightness=float(data.get("max_music_brightness", 1.00)),
        )

