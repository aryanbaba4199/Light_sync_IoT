"""
Center-Outward Radial Angle Spatial Perimeter Sampler for Movie Mode in DevLights.

Architecture:
1. Calculates the optical center of the display / active video region: (cx, cy).
2. Maps each physical LED ball to its coordinate along the perimeter (every centimeter).
3. Projects radial rays and angular sectors (wedges) from (cx, cy) to each ball.
4. Samples color along the angular sector towards the perimeter, avoiding center logo contamination
   and black letterbox bars.
5. In corners, angles sweep continuously through corner vectors (e.g. Top-Left corner is ~ -135°),
   naturally capturing corner colors (e.g. yellow) with zero artificial edge seams.
6. Applies asymmetric temporal filtering (fast attack for dynamic explosions, smooth decay).
"""
import numpy as np
import math
from typing import List, Tuple, Dict, Optional, Any
try:
    from movie_models import MovieLayout, DEFAULT_TOP_LEDS, DEFAULT_RIGHT_LEDS, DEFAULT_BOTTOM_LEDS, DEFAULT_LEFT_LEDS
except ImportError:
    from host.movie_models import MovieLayout, DEFAULT_TOP_LEDS, DEFAULT_RIGHT_LEDS, DEFAULT_BOTTOM_LEDS, DEFAULT_LEFT_LEDS


class MovieSpatialSampler:
    def __init__(self, layout: Optional[MovieLayout] = None):
        self.layout = layout or MovieLayout()
        self.prev_led_colors: Optional[np.ndarray] = None  # Shape: (N, 3)
        self.attack_rate = 0.70   # Fast attack for dynamic explosions
        self.release_rate = 0.25  # Smooth release to eliminate flicker
        self.black_threshold = 12.0  # Luminance cutoff for letterbox detection
        # Radial depth: samples from 0.50 (inner threshold) to 0.98 (near perimeter)
        self.radial_start = 0.50
        self.radial_end = 0.98
        self.num_radial_steps = 6
        self.num_sub_angles = 3

    def update_layout(self, layout: MovieLayout):
        if self.prev_led_colors is not None and len(self.prev_led_colors) != layout.total_leds:
            self.prev_led_colors = None
        self.layout = layout

    def detect_active_video_region(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        """
        Detects letterbox (top/bottom) and pillarbox (left/right) black bars.
        Returns (ymin, ymax, xmin, xmax).
        Falls back to full frame if scene is completely dark or bars are absent.
        """
        h, w = frame.shape[:2]
        if h < 10 or w < 10:
            return 0, h, 0, w

        # Downsample for fast detection
        step_y = max(1, h // 60)
        step_x = max(1, w // 80)
        small = frame[::step_y, ::step_x]

        # Extract RGB channels (handle BGRA or BGR)
        if small.shape[-1] >= 3:
            b = small[:, :, 0].astype(np.float32)
            g = small[:, :, 1].astype(np.float32)
            r = small[:, :, 2].astype(np.float32)
        else:
            return 0, h, 0, w

        # Luminance per downsampled pixel
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b

        # Row-wise and column-wise mean luminance
        row_lum = np.mean(lum, axis=1)
        col_lum = np.mean(lum, axis=0)

        # If full frame is dark, don't crop falsely
        if np.mean(lum) < self.black_threshold:
            return 0, h, 0, w

        small_h = len(row_lum)
        small_w = len(col_lum)

        # Scan top down to mid
        ymin_idx = 0
        for i in range(small_h // 2):
            if row_lum[i] >= self.black_threshold:
                ymin_idx = i
                break

        # Scan bottom up to mid
        ymax_idx = small_h
        for i in range(small_h - 1, small_h // 2, -1):
            if row_lum[i] >= self.black_threshold:
                ymax_idx = i + 1
                break

        # Scan left to mid
        xmin_idx = 0
        for j in range(small_w // 2):
            if col_lum[j] >= self.black_threshold:
                xmin_idx = j
                break

        # Scan right to mid
        xmax_idx = small_w
        for j in range(small_w - 1, small_w // 2, -1):
            if col_lum[j] >= self.black_threshold:
                xmax_idx = j + 1
                break

        ymin = int(ymin_idx * step_y)
        ymax = int(min(h, ymax_idx * step_y))
        xmin = int(xmin_idx * step_x)
        xmax = int(min(w, xmax_idx * step_x))

        # Sanity check: active region must cover at least 30% of each dimension
        if (ymax - ymin < h * 0.30) or (xmax - xmin < w * 0.30):
            return 0, h, 0, w

        return ymin, ymax, xmin, xmax

    def get_perimeter_ball_coordinates(
        self, ymin: int, ymax: int, xmin: int, xmax: int
    ) -> List[Tuple[float, float, str]]:
        """
        Maps each physical LED ball along the perimeter of the active rectangle.
        Returns a list of (x, y, edge_name) for all bulbs in sequence.
        """
        top_count = max(0, int(self.layout.top))
        right_count = max(0, int(self.layout.right))
        bottom_count = max(0, int(self.layout.bottom))
        left_count = max(0, int(self.layout.left))

        w = float(max(1, xmax - xmin))
        h = float(max(1, ymax - ymin))
        fx_min = float(xmin)
        fy_min = float(ymin)
        fx_max = float(xmax)
        fy_max = float(ymax)

        coords: List[Tuple[float, float, str]] = []

        if self.layout.clockwise:
            # 1. TOP EDGE: Left -> Right
            for i in range(top_count):
                frac = (i + 0.5) / max(1, top_count)
                coords.append((fx_min + frac * w, fy_min, "top"))

            # 2. RIGHT EDGE: Top -> Bottom
            for i in range(right_count):
                frac = (i + 0.5) / max(1, right_count)
                coords.append((fx_max, fy_min + frac * h, "right"))

            # 3. BOTTOM EDGE: Right -> Left
            for i in range(bottom_count):
                frac = (i + 0.5) / max(1, bottom_count)
                coords.append((fx_max - frac * w, fy_max, "bottom"))

            # 4. LEFT EDGE: Bottom -> Top
            for i in range(left_count):
                frac = (i + 0.5) / max(1, left_count)
                coords.append((fx_min, fy_max - frac * h, "left"))
        else:
            # Counter-Clockwise
            # 1. TOP EDGE: Right -> Left
            for i in range(top_count):
                frac = (i + 0.5) / max(1, top_count)
                coords.append((fx_max - frac * w, fy_min, "top"))

            # 2. LEFT EDGE: Top -> Bottom
            for i in range(left_count):
                frac = (i + 0.5) / max(1, left_count)
                coords.append((fx_min, fy_min + frac * h, "left"))

            # 3. BOTTOM EDGE: Left -> Right
            for i in range(bottom_count):
                frac = (i + 0.5) / max(1, bottom_count)
                coords.append((fx_min + frac * w, fy_max, "bottom"))

            # 4. RIGHT EDGE: Bottom -> Top
            for i in range(right_count):
                frac = (i + 0.5) / max(1, right_count)
                coords.append((fx_max, fy_max - frac * h, "right"))

        return coords

    def sample_perimeter(
        self, frame: np.ndarray
    ) -> Tuple[List[Tuple[int, int, int]], Dict[str, Tuple[int, int, int]], Tuple[int, int, int, int]]:
        """
        Samples the frame perimeter using Center-Outward Radial Angles.
        
        Returns:
          - per_led_rgb: List of (r, g, b) tuples for each physical LED ball.
          - edge_averages: Dict with average (r, g, b) for "top", "right", "bottom", "left".
          - active_bounds: (ymin, ymax, xmin, xmax).
        """
        total = self.layout.total_leds
        if total == 0:
            return [], {"top": (0, 0, 0), "right": (0, 0, 0), "bottom": (0, 0, 0), "left": (0, 0, 0)}, (0, 0, 0, 0)

        frame_h, frame_w = frame.shape[:2]
        if frame_h == 0 or frame_w == 0:
            return [(0, 0, 0)] * total, {"top": (0, 0, 0), "right": (0, 0, 0), "bottom": (0, 0, 0), "left": (0, 0, 0)}, (0, 0, 0, 0)

        # 1. Detect active video region (handles letterbox/pillarbox)
        ymin, ymax, xmin, xmax = self.detect_active_video_region(frame)
        act_w = max(2, xmax - xmin)
        act_h = max(2, ymax - ymin)

        # 2. Display / Active Center
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        half_w = act_w / 2.0
        half_h = act_h / 2.0

        # 3. Perimeter ball coordinates (every centimeter)
        ball_info = self.get_perimeter_ball_coordinates(ymin, ymax, xmin, xmax)
        if len(ball_info) != total:
            total = len(ball_info)

        # Extract RGB arrays from BGRA / BGR frame (OpenCV / MSS standard)
        # B = frame[..., 0], G = frame[..., 1], R = frame[..., 2]
        if frame.shape[-1] >= 3:
            b_chan = frame[:, :, 0].astype(np.float32)
            g_chan = frame[:, :, 1].astype(np.float32)
            r_chan = frame[:, :, 2].astype(np.float32)
        else:
            return [(0, 0, 0)] * total, {"top": (0, 0, 0), "right": (0, 0, 0), "bottom": (0, 0, 0), "left": (0, 0, 0)}, (ymin, ymax, xmin, xmax)

        # Precompute angles for each ball
        angles = []
        for bx, by, _ in ball_info:
            dx = bx - cx
            dy = by - cy
            angles.append(math.atan2(dy, dx))

        # Radial step percentages (outer radius towards perimeter)
        r_steps = np.linspace(self.radial_start, self.radial_end, self.num_radial_steps)
        # Weight points nearer to perimeter slightly higher: w(r) = r^1.2
        r_weights = np.power(r_steps, 1.2)
        r_weights /= np.sum(r_weights)

        raw_colors = np.zeros((total, 3), dtype=np.float32)

        for i, (bx, by, edge_name) in enumerate(ball_info):
            theta = angles[i]

            # Angular width of this ball's sector
            prev_theta = angles[(i - 1 + total) % total]
            next_theta = angles[(i + 1) % total]
            diff1 = abs(math.atan2(math.sin(theta - prev_theta), math.cos(theta - prev_theta)))
            diff2 = abs(math.atan2(math.sin(next_theta - theta), math.cos(next_theta - theta)))
            d_theta = max(0.005, (diff1 + diff2) / 2.0)

            # Sub-angles across the ball's angular wedge
            sub_angles = [
                theta - 0.25 * d_theta,
                theta,
                theta + 0.25 * d_theta,
            ]

            ball_r = 0.0
            ball_g = 0.0
            ball_b = 0.0
            total_weight = 0.0

            for ang in sub_angles:
                cos_a = math.cos(ang)
                sin_a = math.sin(ang)

                # Distance from center to active perimeter boundary along angle ang
                denom_x = abs(cos_a) + 1e-6
                denom_y = abs(sin_a) + 1e-6
                t_bound = min(half_w / denom_x, half_h / denom_y)

                for r_frac, w_val in zip(r_steps, r_weights):
                    sx = int(round(cx + r_frac * t_bound * cos_a))
                    sy = int(round(cy + r_frac * t_bound * sin_a))

                    # Clamp strictly inside active video bounds and frame bounds
                    sx = max(xmin, min(xmax - 1, min(frame_w - 1, max(0, sx))))
                    sy = max(ymin, min(ymax - 1, min(frame_h - 1, max(0, sy))))

                    ball_r += r_chan[sy, sx] * w_val
                    ball_g += g_chan[sy, sx] * w_val
                    ball_b += b_chan[sy, sx] * w_val
                    total_weight += w_val

            if total_weight > 0.0:
                raw_colors[i, 0] = ball_r / total_weight
                raw_colors[i, 1] = ball_g / total_weight
                raw_colors[i, 2] = ball_b / total_weight

        # 4. Asymmetric Temporal Filtering (fast attack, smooth release)
        if self.prev_led_colors is None or len(self.prev_led_colors) != total:
            smoothed_colors = raw_colors.copy()
        else:
            smoothed_colors = np.zeros_like(raw_colors)
            for i in range(total):
                for c in range(3):
                    target = raw_colors[i, c]
                    current = self.prev_led_colors[i, c]
                    if target > current:
                        smoothed_colors[i, c] = current + self.attack_rate * (target - current)
                    else:
                        smoothed_colors[i, c] = current + self.release_rate * (target - current)

        self.prev_led_colors = smoothed_colors.copy()

        # 5. Format per-LED RGB tuples
        per_led_rgb: List[Tuple[int, int, int]] = []
        for i in range(total):
            r = int(np.clip(round(smoothed_colors[i, 0]), 0, 255))
            g = int(np.clip(round(smoothed_colors[i, 1]), 0, 255))
            b = int(np.clip(round(smoothed_colors[i, 2]), 0, 255))
            per_led_rgb.append((r, g, b))

        # 6. Edge averages
        edge_colors: Dict[str, List[Tuple[int, int, int]]] = {
            "top": [], "right": [], "bottom": [], "left": []
        }
        for i, (_, _, edge_name) in enumerate(ball_info):
            if i < len(per_led_rgb):
                edge_colors[edge_name].append(per_led_rgb[i])

        edge_averages: Dict[str, Tuple[int, int, int]] = {}
        for edge_name, clist in edge_colors.items():
            if clist:
                avg_r = int(np.mean([c[0] for c in clist]))
                avg_g = int(np.mean([c[1] for c in clist]))
                avg_b = int(np.mean([c[2] for c in clist]))
                edge_averages[edge_name] = (avg_r, avg_g, avg_b)
            else:
                edge_averages[edge_name] = (0, 0, 0)

        return per_led_rgb, edge_averages, (ymin, ymax, xmin, xmax)
