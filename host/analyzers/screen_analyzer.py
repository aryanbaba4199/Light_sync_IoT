import mss
import numpy as np
import time
import threading
import sys
import logging
from .color_extractor import ColorExtractor

logger = logging.getLogger(__name__)

class ScreenAnalyzer:
    def __init__(self, lighting_engine):
        self.lighting_engine = lighting_engine
        self.running = False
        self.thread = None
        self.fps = 15
        self.status = "stopped" # 'stopped', 'running', 'permission_denied', 'error'
        self.sct = None
        
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

    def _capture_loop(self):
        try:
            monitors = self.sct.monitors
            monitor = monitors[1] if len(monitors) > 1 else monitors[0]
            
            # Sub-region capture for performance (center of screen)
            cx, cy = monitor["left"] + monitor["width"] // 2, monitor["top"] + monitor["height"] // 2
            bbox = {
                "top": max(monitor["top"], cy - 360),
                "left": max(monitor["left"], cx - 480),
                "width": min(monitor["width"], 960),
                "height": min(monitor["height"], 720)
            }
        except Exception:
            # Fallback to full primary display
            bbox = self.sct.monitors[0] if self.sct and self.sct.monitors else {"top":0, "left":0, "width":1920, "height":1080}

        target_frame_time = 1.0 / self.fps

        while self.running and self.sct:
            start_time = time.time()
            try:
                # Capture the screen region
                sct_img = self.sct.grab(bbox)
                img = np.array(sct_img)
                
                # Aggressively downsample to reduce CPU usage
                # We only need ambient color, so 1 out of every 20 pixels is plenty
                small_img = img[::20, ::20]
                
                # Extract the dominant/ambient color
                r, g, b = ColorExtractor.extract_ambient_color(small_img)
                
                # Send to engine
                self.lighting_engine.set_ambient_color(r, g, b)
                
                # Diagnostics
                capture_ms = (time.time() - start_time) * 1000.0
                import diagnostics as diag
                diag.diagnostics.set_metric("screen_capture_ms", capture_ms)
                
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
