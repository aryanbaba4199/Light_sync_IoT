"""
Spatial Perimeter Video Sampler for Movie Mode in DevLights.

Performs:
1. Active Video Region Detection (letterbox / pillarbox black-bar cropping).
2. Perimeter Edge Slicing with position-aware LED gradients.
3. Trimmed / luminance-weighted aggregation per spatial window.
4. Seamless Corner Smoothing across adjacent edges.
5. Asymmetric Temporal Color Filtering (fast attack for explosions, smooth release).
"""
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
try:
    from movie_models import MovieLayout, DEFAULT_TOP_LEDS, DEFAULT_RIGHT_LEDS, DEFAULT_BOTTOM_LEDS, DEFAULT_LEFT_LEDS
except ImportError:
    from host.movie_models import MovieLayout, DEFAULT_TOP_LEDS, DEFAULT_RIGHT_LEDS, DEFAULT_BOTTOM_LEDS, DEFAULT_LEFT_LEDS


class MovieSpatialSampler:
    def __init__(self, layout: Optional[MovieLayout] = None):
        self.layout = layout or MovieLayout()
        self.prev_led_colors: Optional[np.ndarray] = None  # Shape: (N, 3)
        self.attack_rate = 0.75   # Fast attack for explosions and dynamic action
        self.release_rate = 0.25  # Smooth release to prevent high-frequency flicker
        self.black_threshold = 12.0  # Luminance cutoff for letterbox / black bar detection

    def update_layout(self, layout: MovieLayout):
        if layout.total_leds != (len(self.prev_led_colors) if self.prev_led_colors is not None else 0):
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

        # Extract RGB channels (handle BGRA or BGR/RGB)
        if small.shape[-1] == 4:
            b = small[:, :, 0].astype(np.float32)
            g = small[:, :, 1].astype(np.float32)
            r = small[:, :, 2].astype(np.float32)
        elif small.shape[-1] == 3:
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

        # Check overall luminance: if full frame is dark, don't crop falsely
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

        # Convert downsampled indices back to original frame coordinates
        ymin = int(ymin_idx * step_y)
        ymax = int(min(h, ymax_idx * step_y))
        xmin = int(xmin_idx * step_x)
        xmax = int(min(w, xmax_idx * step_x))

        # Sanity check: active region must cover at least 30% of each dimension
        if (ymax - ymin < h * 0.30) or (xmax - xmin < w * 0.30):
            return 0, h, 0, w

        return ymin, ymax, xmin, xmax

    def _sample_region_color(self, region: np.ndarray) -> np.ndarray:
        """
        Computes robust RGB from a sub-region using luminance-weighted averaging.
        Returns float array [r, g, b].
        """
        if region.size == 0:
            return np.array([0.0, 0.0, 0.0], dtype=np.float32)

        # Flatten spatial pixels
        pixels = region.reshape(-1, region.shape[-1])
        if pixels.shape[-1] >= 3:
            # Assume BGR(A) input from screen capture (standard for mss/OpenCV)
            b = pixels[:, 0].astype(np.float32)
            g = pixels[:, 1].astype(np.float32)
            r = pixels[:, 2].astype(np.float32)
        else:
            return np.array([0.0, 0.0, 0.0], dtype=np.float32)

        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        max_lum = float(np.max(lum))

        if max_lum < 5.0:
            # Truly black or near-black region
            return np.array([float(np.mean(r)), float(np.mean(g)), float(np.mean(b))], dtype=np.float32)

        # Filter out extreme dark pixels if illuminated content exists in the window
        valid_mask = lum >= max(8.0, max_lum * 0.15)
        if np.any(valid_mask):
            return np.array([
                float(np.mean(r[valid_mask])),
                float(np.mean(g[valid_mask])),
                float(np.mean(b[valid_mask]))
            ], dtype=np.float32)

        return np.array([float(np.mean(r)), float(np.mean(g)), float(np.mean(b))], dtype=np.float32)

    def sample_perimeter(self, frame: np.ndarray) -> Tuple[List[Tuple[int, int, int]], Dict[str, Tuple[int, int, int]], Tuple[int, int, int, int]]:
        """
        Spatially samples the video frame perimeter according to self.layout.
        Returns:
          - per_led_rgb: List of (r, g, b) tuples for each physical LED.
          - edge_averages: Dict with average (r, g, b) for "top", "right", "bottom", "left".
          - active_bounds: (ymin, ymax, xmin, xmax).
        """
        total = self.layout.total_leds
        if total == 0:
            return [], {"top": (0, 0, 0), "right": (0, 0, 0), "bottom": (0, 0, 0), "left": (0, 0, 0)}, (0, 0, 0, 0)

        # 1. Detect active video region (handles letterboxing/pillarboxing)
        ymin, ymax, xmin, xmax = self.detect_active_video_region(frame)
        act_h = max(1, ymax - ymin)
        act_w = max(1, xmax - xmin)

        thickness = float(self.layout.sampling_thickness)
        dy = max(2, min(act_h // 2, int(act_h * thickness)))
        dx = max(2, min(act_w // 2, int(act_w * thickness)))

        raw_led_colors = np.zeros((total, 3), dtype=np.float32)
        edge_ranges = self.layout.get_edge_ranges()

        # ── TOP EDGE ──────────────────────────────────────────────────────────
        top_start, top_end = edge_ranges["top"]
        top_count = top_end - top_start
        if top_count > 0:
            slice_w = max(2, act_w / top_count)
            top_strip = frame[ymin : ymin + dy, xmin : xmax]
            for i in range(top_count):
                idx = top_start + i
                t = (i + 0.5) / top_count
                center_x = int(t * act_w)
                x_start = max(0, int(center_x - slice_w * 0.8))
                x_end = min(act_w, int(center_x + slice_w * 0.8 + 1))
                window = top_strip[:, x_start:x_end]
                raw_led_colors[idx] = self._sample_region_color(window)

        # ── RIGHT EDGE ────────────────────────────────────────────────────────
        right_start, right_end = edge_ranges["right"]
        right_count = right_end - right_start
        if right_count > 0:
            slice_h = max(2, act_h / right_count)
            right_strip = frame[ymin : ymax, max(0, xmax - dx) : xmax]
            for i in range(right_count):
                idx = right_start + i
                t = (i + 0.5) / right_count
                center_y = int(t * act_h)
                y_start = max(0, int(center_y - slice_h * 0.8))
                y_end = min(act_h, int(center_y + slice_h * 0.8 + 1))
                window = right_strip[y_start:y_end, :]
                raw_led_colors[idx] = self._sample_region_color(window)

        # ── BOTTOM EDGE (Clockwise: Right to Left) ───────────────────────────
        bottom_start, bottom_end = edge_ranges["bottom"]
        bottom_count = bottom_end - bottom_start
        if bottom_count > 0:
            slice_w = max(2, act_w / bottom_count)
            bottom_strip = frame[max(0, ymax - dy) : ymax, xmin : xmax]
            for i in range(bottom_count):
                idx = bottom_start + i
                # Clockwise: start from right (x=act_w) to left (x=0)
                t = (i + 0.5) / bottom_count
                center_x = int(act_w - t * act_w)
                x_start = max(0, int(center_x - slice_w * 0.8))
                x_end = min(act_w, int(center_x + slice_w * 0.8 + 1))
                window = bottom_strip[:, x_start:x_end]
                raw_led_colors[idx] = self._sample_region_color(window)

        # ── LEFT EDGE (Clockwise: Bottom to Top) ─────────────────────────────
        left_start, left_end = edge_ranges["left"]
        left_count = left_end - left_start
        if left_count > 0:
            slice_h = max(2, act_h / left_count)
            left_strip = frame[ymin : ymax, xmin : xmin + dx]
            for i in range(left_count):
                idx = left_start + i
                # Clockwise: start from bottom (y=act_h) to top (y=0)
                t = (i + 0.5) / left_count
                center_y = int(act_h - t * act_h)
                y_start = max(0, int(center_y - slice_h * 0.8))
                y_end = min(act_h, int(center_y + slice_h * 0.8 + 1))
                window = left_strip[y_start:y_end, :]
                raw_led_colors[idx] = self._sample_region_color(window)

        # 2. Corner Smoothing (blend adjacent edge boundaries to eliminate harsh seams)
        raw_led_colors = self._apply_corner_smoothing(raw_led_colors, edge_ranges)

        # 3. Asymmetric Temporal Filtering (Fast Attack, Smooth Release)
        if self.prev_led_colors is None or len(self.prev_led_colors) != total:
            self.prev_led_colors = raw_led_colors.copy()
            smoothed = raw_led_colors
        else:
            prev_lum = 0.2126 * self.prev_led_colors[:, 0] + 0.7152 * self.prev_led_colors[:, 1] + 0.0722 * self.prev_led_colors[:, 2]
            target_lum = 0.2126 * raw_led_colors[:, 0] + 0.7152 * raw_led_colors[:, 1] + 0.0722 * raw_led_colors[:, 2]

            # Vectorized attack vs release mask
            is_attack = target_lum > prev_lum
            rate = np.where(is_attack[:, None], self.attack_rate, self.release_rate)
            smoothed = self.prev_led_colors * (1.0 - rate) + raw_led_colors * rate
            self.prev_led_colors = smoothed.copy()

        # Format output
        final_leds: List[Tuple[int, int, int]] = []
        for i in range(total):
            r = int(np.clip(smoothed[i, 0], 0, 255))
            g = int(np.clip(smoothed[i, 1], 0, 255))
            b = int(np.clip(smoothed[i, 2], 0, 255))
            final_leds.append((r, g, b))

        # Compute clean edge averages
        edge_averages: Dict[str, Tuple[int, int, int]] = {}
        for edge_name, (s, e) in edge_ranges.items():
            if e > s:
                edge_slice = smoothed[s:e]
                avg_r = int(np.clip(np.mean(edge_slice[:, 0]), 0, 255))
                avg_g = int(np.clip(np.mean(edge_slice[:, 1]), 0, 255))
                avg_b = int(np.clip(np.mean(edge_slice[:, 2]), 0, 255))
                edge_averages[edge_name] = (avg_r, avg_g, avg_b)
            else:
                edge_averages[edge_name] = (0, 0, 0)

        return final_leds, edge_averages, (ymin, ymax, xmin, xmax)

    def _apply_corner_smoothing(self, colors: np.ndarray, ranges: Dict[str, Tuple[int, int]], corner_radius: int = 3) -> np.ndarray:
        """
        Blends colors smoothly at the 4 corner joints of the perimeter.
        """
        edges = ["top", "right", "bottom", "left"]
        num_edges = len(edges)
        res = colors.copy()

        for idx, edge in enumerate(edges):
            next_edge = edges[(idx + 1) % num_edges]
            s1, e1 = ranges[edge]
            s2, e2 = ranges[next_edge]
            if (e1 - s1) < 2 or (e2 - s2) < 2:
                continue

            # Joint is between e1 - 1 and s2
            # Blend the last corner_radius LEDs of edge 1 with the first corner_radius LEDs of edge 2
            k = min(corner_radius, (e1 - s1) // 2, (e2 - s2) // 2)
            c1 = colors[e1 - 1]
            c2 = colors[s2]
            corner_mid = 0.5 * c1 + 0.5 * c2

            for step in range(k):
                weight = float(step + 1) / float(k + 1)  # 0.25, 0.5, 0.75
                # Edge 1 end fades toward corner_mid
                idx1 = e1 - 1 - (k - 1 - step)
                res[idx1] = colors[idx1] * (1.0 - 0.4 * weight) + corner_mid * (0.4 * weight)
                # Edge 2 start fades from corner_mid
                idx2 = s2 + step
                res[idx2] = colors[idx2] * (1.0 - 0.4 * (1.0 - weight)) + corner_mid * (0.4 * (1.0 - weight))

        return res
