import unittest
import numpy as np
from host.analyzers.color_extractor import ColorExtractor
from host.analyzers.screen_analyzer import ScreenAnalyzer

class DummyLightingEngine:
    def __init__(self):
        self.r = 0
        self.g = 0
        self.b = 0
        
    def set_ambient_color(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

class TestColorExtractor(unittest.TestCase):
    def test_pure_colors(self):
        # Create a tiny 2x2 image of pure red (in BGRA since mss gives BGRA)
        # B, G, R, A
        red_img = np.array([
            [[0, 0, 255, 255], [0, 0, 255, 255]],
            [[0, 0, 255, 255], [0, 0, 255, 255]]
        ], dtype=np.uint8)
        
        r, g, b = ColorExtractor.extract_ambient_color(red_img)
        self.assertEqual((r, g, b), (255, 0, 0))
        
        green_img = np.array([
            [[0, 255, 0, 255], [0, 255, 0, 255]],
            [[0, 255, 0, 255], [0, 255, 0, 255]]
        ], dtype=np.uint8)
        r, g, b = ColorExtractor.extract_ambient_color(green_img)
        self.assertEqual((r, g, b), (0, 255, 0))

        blue_img = np.array([
            [[255, 0, 0, 255], [255, 0, 0, 255]],
            [[255, 0, 0, 255], [255, 0, 0, 255]]
        ], dtype=np.uint8)
        r, g, b = ColorExtractor.extract_ambient_color(blue_img)
        self.assertEqual((r, g, b), (0, 0, 255))
        
    def test_black_and_white(self):
        white_img = np.array([
            [[255, 255, 255, 255], [255, 255, 255, 255]],
            [[255, 255, 255, 255], [255, 255, 255, 255]]
        ], dtype=np.uint8)
        r, g, b = ColorExtractor.extract_ambient_color(white_img)
        self.assertEqual((r, g, b), (255, 255, 255))

        black_img = np.array([
            [[0, 0, 0, 255], [0, 0, 0, 255]],
            [[0, 0, 0, 255], [0, 0, 0, 255]]
        ], dtype=np.uint8)
        r, g, b = ColorExtractor.extract_ambient_color(black_img)
        self.assertEqual((r, g, b), (0, 0, 0))
        
    def test_mixed_with_dark_borders(self):
        # 3x3 image. Top and bottom are black (like letterbox in movies)
        # Center is blue.
        mixed_img = np.array([
            [[0, 0, 0, 255], [0, 0, 0, 255], [0, 0, 0, 255]],
            [[255, 0, 0, 255], [255, 0, 0, 255], [255, 0, 0, 255]],
            [[0, 0, 0, 255], [0, 0, 0, 255], [0, 0, 0, 255]]
        ], dtype=np.uint8)
        
        # The algorithm should filter out the dark pixels and only average the blue ones!
        r, g, b = ColorExtractor.extract_ambient_color(mixed_img)
        self.assertEqual((r, g, b), (0, 0, 255))

    def test_completely_dark_scene(self):
        # A scene that is just very dark gray (luminance < 10)
        dark_img = np.array([
            [[5, 5, 5, 255], [5, 5, 5, 255]],
            [[5, 5, 5, 255], [5, 5, 5, 255]]
        ], dtype=np.uint8)
        
        r, g, b = ColorExtractor.extract_ambient_color(dark_img)
        # Should fallback to naive average
        self.assertEqual((r, g, b), (5, 5, 5))

class TestScreenAnalyzerLifecycle(unittest.TestCase):
    def test_lifecycle(self):
        engine = DummyLightingEngine()
        analyzer = ScreenAnalyzer(engine)
        
        self.assertEqual(analyzer.status, "stopped")
        self.assertFalse(analyzer.running)
        
        # Skip actual thread start in tests by mocking mss? 
        # Actually it's fine, start() will spawn the thread and we can stop it immediately.
        # But if permissions are denied on CI, it will safely handle it.
        analyzer.start()
        
        # Could be running or permission_denied or error
        self.assertIn(analyzer.status, ["running", "permission_denied", "error"])
        
        analyzer.stop()
        self.assertEqual(analyzer.status, "stopped")
        self.assertFalse(analyzer.running)

if __name__ == '__main__':
    unittest.main()
