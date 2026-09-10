import mss
import numpy as np
import time
import threading
import sys
import logging
from typing import List, Dict, Any, Tuple, Optional
from .color_extractor import ColorExtractor

try:
    from .movie_spatial_sampler import MovieSpatialSampler
except ImportError:
    from analyzers.movie_spatial_sampler import MovieSpatialSampler
try:
    from movie_models import MovieLayout
except ImportError:
    from host.movie_models import MovieLayout

logger = logging.getLogger(__name__)

class ScreenAnalyzer:
    def __init__(self, lighting_engine):
        self.lighting_engine = lighting_engine
        self.running = False
        self.thread = None
        self.fps = 20  # Responsive 20 FPS real-time capture
        self.status = "stopped"  # 'stopped', 'running', 'permission_denied', 'error'
        self.sct = None
        self.movie_sampler = MovieSpatialSampler()
        
    def _check_macos_permissions(self):
        if sys.platform != 'darwin':
            return True
        try:
            import Quartz
            if hasattr(Quartz, 'CGPreflightScreenCaptureAccess'):
                has_access = Quartz.CGPreflightScreenCaptureAccess()
                if not has_access:
                    # Request access (will pop up the OS dialog if not previously denied)
                    if hasattr(Quartz, 'CGRequestScreenCaptureAccess'):
                        Quartz.CGRequestScreenCaptureAccess()
                    return False
        except Exception as e:
            logger.error(f"Failed to check macOS permissions: {e}")
        return True

    def start(self):
        if self.running:
            return
            
        if not self._check_macos_permissions():
            self.status = "permission_denied"
            logger.warning("Screen Capture Permission Denied (macOS)")
            return

        try:
            self.sct = mss.MSS()
        except Exception as e:
            self.status = "error"
            logger.error(f"Failed to initialize mss: {e}")
            return
            
        self.running = True
        self.status = "running"
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info("Screen Analyzer started.")

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.status = "stopped"
        if self.sct:
            self.sct.close()
            self.sct = None
        logger.info("Screen Analyzer stopped.")

    @staticmethod
    def get_available_monitors() -> List[Dict[str, Any]]:
        """
        Returns a list of connected physical displays.
        Index 1 is typically the primary display; index 0 is the combined virtual desktop.
        """
        results = []
        try:
            with mss.MSS() as sct:
                for idx, m in enumerate(sct.monitors):
                    if idx == 0 and len(sct.monitors) > 1:
                        continue  # Skip combined bounding box if multiple monitors exist
                    results.append({
                        "id": idx,
                        "name": f"Display {idx} ({m['width']} × {m['height']})",
                        "width": m["width"],
                        "height": m["height"],
                        "left": m["left"],
                        "top": m["top"],
                    })
        except Exception as e:
            logger.error(f"Failed to query monitors: {e}")
        return results

    def _capture_loop(self):
        target_frame_time = 1.0 / self.fps

        while self.running and self.sct:
            start_time = time.time()
            try:
                # Dynamic monitor selection
                target_monitor_idx = 1
                app_state = getattr(self.lighting_engine, "app_state", None)
                if app_state and hasattr(app_state, "settings"):
                    movie_settings = app_state.settings.get("movie", {})
                    target_monitor_idx = int(movie_settings.get("monitor_index", 1))

                monitors = self.sct.monitors
                if 1 <= target_monitor_idx < len(monitors):
                    monitor = monitors[target_monitor_idx]
                elif len(monitors) > 1:
                    monitor = monitors[1]
                elif len(monitors) > 0:
                    monitor = monitors[0]
                else:
                    monitor = {"top": 0, "left": 0, "width": 1920, "height": 1080}

                bbox = {
                    "top": monitor["top"],
                    "left": monitor["left"],
                    "width": monitor["width"],
                    "height": monitor["height"]
                }

                # Capture the display
                sct_img = self.sct.grab(bbox)
                img = np.array(sct_img)

                is_movie_mode = False
                if app_state and getattr(app_state, "mode", None) == "movie":
                    is_movie_mode = True

                if is_movie_mode:
                    # Sync layout if changed
                    if hasattr(app_state, "get_movie_layout"):
                        current_layout = app_state.get_movie_layout()
                        self.movie_sampler.update_layout(current_layout)

                    # Downsample slightly for ultra-fast spatial sampling (~480-540p)
                    step = max(1, img.shape[0] // 480)
                    sample_frame = img[::step, ::step]

                    led_colors, edge_averages, active_bounds = self.movie_sampler.sample_perimeter(sample_frame)


                    # Forward spatial LED buffer to lighting engine
                    if hasattr(self.lighting_engine, "process_movie_frame"):
                        self.lighting_engine.process_movie_frame(led_colors, edge_averages)

                    # Compute overall perimeter brightness/color for fallback / diagnostics
                    if led_colors:
                        r_vals = [c[0] for c in led_colors]
                        g_vals = [c[1] for c in led_colors]
                        b_vals = [c[2] for c in led_colors]
                        avg_r = int(np.mean(r_vals))
                        avg_g = int(np.mean(g_vals))
                        avg_b = int(np.mean(b_vals))
                    else:
                        avg_r, avg_g, avg_b = 0, 0, 0

                    intensity = min(1.0, max(avg_r, max(avg_g, avg_b)) / 255.0)

                    if hasattr(self.lighting_engine, "set_ambient_color"):
                        self.lighting_engine.set_ambient_color(avg_r, avg_g, avg_b)
                    if hasattr(self.lighting_engine, "set_ambient_brightness"):
                        self.lighting_engine.set_ambient_brightness(intensity)

                    # Telemetry metrics
                    try:
                        import diagnostics as diag
                        diag.diagnostics.set_metric("movie_top_rgb", edge_averages.get("top", (0, 0, 0)))
                        diag.diagnostics.set_metric("movie_right_rgb", edge_averages.get("right", (0, 0, 0)))
                        diag.diagnostics.set_metric("movie_bottom_rgb", edge_averages.get("bottom", (0, 0, 0)))
                        diag.diagnostics.set_metric("movie_left_rgb", edge_averages.get("left", (0, 0, 0)))
                    except Exception:
                        pass

                else:
                    # Legacy fallback for Game and other single-ambient screen modes
                    small_img = img[::20, ::20]
                    r, g, b = ColorExtractor.extract_ambient_color(small_img)
                    intensity = min(1.0, max(r, max(g, b)) / 255.0)

                    if hasattr(self.lighting_engine, "set_ambient_color"):
                        self.lighting_engine.set_ambient_color(r, g, b)
                    if hasattr(self.lighting_engine, "set_ambient_brightness"):
                        self.lighting_engine.set_ambient_brightness(intensity)

                # Diagnostics
                capture_ms = (time.time() - start_time) * 1000.0
                try:
                    import diagnostics as diag
                    diag.diagnostics.set_metric("screen_capture_ms", capture_ms)
                except Exception:
                    pass
                
            except mss.exception.ScreenShotError as e:
                self.status = "permission_denied"
                self.running = False
                logger.error(f"Screenshot error (possibly permission denied): {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected capture error: {e}")
                
            elapsed = time.time() - start_time
            sleep_time = max(0, target_frame_time - elapsed)
            time.sleep(sleep_time)
