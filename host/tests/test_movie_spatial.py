"""
Unit and Integration Tests for Movie Mode Spatial Perimeter Sampling and Music Sync.
"""
import sys
import os
import time
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from movie_models import MovieLayout, MovieSettings, DEFAULT_TOTAL_LEDS
from analyzers.movie_spatial_sampler import MovieSpatialSampler
from app_state import AppState, AppMode
from lighting_engine import LightingEngine
from transports import VirtualTransport
from music_models import MusicAnalysis


class TestMovieLayout(unittest.TestCase):
    def test_default_layout(self):
        layout = MovieLayout()
        self.assertEqual(layout.top, 100)
        self.assertEqual(layout.right, 50)
        self.assertEqual(layout.bottom, 100)
        self.assertEqual(layout.left, 50)
        self.assertEqual(layout.total_leds, 300)
        self.assertEqual(layout.sampling_thickness, 0.10)
        self.assertTrue(layout.clockwise)

        ok, err = layout.validate()
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_edge_ranges_clockwise(self):
        layout = MovieLayout(top=100, right=50, bottom=100, left=50, clockwise=True)
        ranges = layout.get_edge_ranges()
        self.assertEqual(ranges["top"], (0, 100))
        self.assertEqual(ranges["right"], (100, 150))
        self.assertEqual(ranges["bottom"], (150, 250))
        self.assertEqual(ranges["left"], (250, 300))

    def test_validation_edge_cases(self):
        # Negative counts
        bad_layout = MovieLayout(top=-5, right=50, bottom=100, left=50)
        ok, err = bad_layout.validate()
        self.assertFalse(ok)
        self.assertIn("negative", err.lower())

        # Zero bulbs
        zero_layout = MovieLayout(top=0, right=0, bottom=0, left=0)
        ok, err = zero_layout.validate()
        self.assertFalse(ok)
        self.assertIn("greater than 0", err.lower())

        # Invalid thickness
        bad_thick = MovieLayout(sampling_thickness=0.50)
        ok, err = bad_thick.validate()
        self.assertFalse(ok)
        self.assertIn("sampling thickness", err.lower())

    def test_serialization(self):
        layout = MovieLayout(top=80, right=40, bottom=80, left=40, sampling_thickness=0.15, clockwise=False)
        d = layout.to_dict()
        self.assertEqual(d["top"], 80)
        self.assertEqual(d["total_leds"], 240)
        self.assertFalse(d["clockwise"])

        restored = MovieLayout.from_dict(d)
        self.assertEqual(restored.top, 80)
        self.assertEqual(restored.right, 40)
        self.assertEqual(restored.total_leds, 240)
        self.assertFalse(restored.clockwise)


class TestMovieSpatialSampler(unittest.TestCase):
    def setUp(self):
        self.layout = MovieLayout(top=100, right=50, bottom=100, left=50)
        self.sampler = MovieSpatialSampler(self.layout)
        self.width = 1280
        self.height = 720

    def _create_frame(self, bg_color=(0, 0, 0)):
        # BGRA format
        frame = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        frame[:, :, 0] = bg_color[2]  # B
        frame[:, :, 1] = bg_color[1]  # G
        frame[:, :, 2] = bg_color[0]  # R
        frame[:, :, 3] = 255
        return frame

    def test_pure_black_frame(self):
        """A black frame should yield 0s across all LEDs without errors."""
        black_frame = self._create_frame((0, 0, 0))
        leds, edges, bounds = self.sampler.sample_perimeter(black_frame)
        self.assertEqual(len(leds), 300)
        self.assertEqual(edges["top"], (0, 0, 0))
        self.assertEqual(edges["right"], (0, 0, 0))
        self.assertEqual(edges["bottom"], (0, 0, 0))
        self.assertEqual(edges["left"], (0, 0, 0))
        for r, g, b in leds:
            self.assertEqual((r, g, b), (0, 0, 0))

    def test_spatial_separation_left_red_right_black(self):
        """Red on left half, black on right half. Left LEDs should be red, Right should be dark."""
        frame = self._create_frame()
        # Set left half to bright red (BGRA: B=0, G=0, R=255)
        frame[:, : self.width // 2, 2] = 255

        leds, edges, bounds = self.sampler.sample_perimeter(frame)
        self.assertGreater(edges["left"][0], 220)
        self.assertEqual(edges["left"][1], 0)
        self.assertEqual(edges["left"][2], 0)

        self.assertEqual(edges["right"], (0, 0, 0))

    def test_spatial_separation_top_green_bottom_black(self):
        """Green on top half, black on bottom half. Top LEDs should be green, Bottom should be dark."""
        frame = self._create_frame()
        frame[: self.height // 2, :, 1] = 255

        leds, edges, bounds = self.sampler.sample_perimeter(frame)
        self.assertGreater(edges["top"][1], 220)
        self.assertEqual(edges["top"][0], 0)
        self.assertEqual(edges["top"][2], 0)

        self.assertEqual(edges["bottom"], (0, 0, 0))

    def test_letterbox_detection_active_content(self):
        """2.39:1 letterbox frame: black bars on top and bottom must be cropped, sampling real movie content."""
        frame = self._create_frame()
        # Active movie is blue in rows 120..600
        frame[120:600, :, 0] = 255  # Blue

        leds, edges, bounds = self.sampler.sample_perimeter(frame)
        ymin, ymax, xmin, xmax = bounds
        self.assertGreaterEqual(ymin, 100)
        self.assertLessEqual(ymax, 620)

        # All perimeter edges should pick up the blue movie content, not black bars
        self.assertGreater(edges["top"][2], 200)
        self.assertGreater(edges["bottom"][2], 200)
        self.assertGreater(edges["left"][2], 200)
        self.assertGreater(edges["right"][2], 200)

    def test_user_reported_scenario_top_red_topleft_yellow_left_yellow(self):
        """
        User scenario:
        - Top is Red
        - Left is Yellow
        - Left-Top corner is Yellow
        - Bottom and Right are Dark
        Radial Angle Sampler must correctly resolve Yellow in corner and left, Red on top, Black on right/bottom.
        """
        frame = self._create_frame()
        # Top region is red (BGRA: B=0, G=0, R=255)
        frame[0 : self.height // 3, :, 2] = 255
        # Left region is yellow (BGRA: B=0, G=255, R=255)
        frame[:, 0 : self.width // 4, 1] = 255
        frame[:, 0 : self.width // 4, 2] = 255

        leds, edges, bounds = self.sampler.sample_perimeter(frame)

        # Top-mid LED (around index 50): should be Red (R > 200, G < 50, B < 50)
        self.assertGreater(leds[50][0], 200)
        self.assertLess(leds[50][1], 50)
        self.assertLess(leds[50][2], 50)

        # Left-Top corner (LED 0 and LED 299): should be Yellow (R > 200, G > 180)
        self.assertGreater(leds[0][0], 200)
        self.assertGreater(leds[0][1], 180)
        self.assertGreater(leds[299][0], 200)
        self.assertGreater(leds[299][1], 180)

        # Left-mid LED (around index 275): should be Yellow (R > 200, G > 180)
        self.assertGreater(leds[275][0], 200)
        self.assertGreater(leds[275][1], 180)

        # Right-mid LED (around index 125): should be Black (0, 0, 0)
        self.assertEqual(leds[125], (0, 0, 0))

        # Bottom-mid LED (around index 200): should be Black (0, 0, 0)
        self.assertEqual(leds[200], (0, 0, 0))



class TestLightingEngineMovieMode(unittest.TestCase):
    def setUp(self):
        self.test_config = "test_movie_engine_config.json"
        if os.path.exists(self.test_config):
            os.remove(self.test_config)
        self.app_state = AppState(self.test_config)
        self.app_state.set_mode(AppMode.MOVIE)
        self.transport = VirtualTransport()
        self.transport.connect()
        self.engine = LightingEngine(self.transport, self.app_state)
        self.engine.smoothing_factor = 0.0

    def tearDown(self):
        self.engine.stop()
        if os.path.exists(self.test_config):
            os.remove(self.test_config)

    def test_movie_spatial_frame_processing(self):
        """Feeding spatial movie frame renders into 300-LED buffer and emits Protocol V2 zones."""
        # Create gradient colors: 100 red (top), 50 green (right), 100 blue (bottom), 50 yellow (left)
        movie_colors = (
            [(255, 0, 0)] * 100 +
            [(0, 255, 0)] * 50 +
            [(0, 0, 255)] * 100 +
            [(255, 255, 0)] * 50
        )
        self.engine.process_movie_frame(movie_colors)
        self.engine.set_user_brightness(1.0)
        time.sleep(0.12)

        # Verify 300 LEDs received
        self.assertEqual(len(self.engine.led_frame), 300)
        # Top segment
        self.assertEqual(self.engine.led_frame[10], (255, 0, 0))
        # Right segment
        self.assertEqual(self.engine.led_frame[120], (0, 255, 0))
        # Bottom segment
        self.assertEqual(self.engine.led_frame[200], (0, 0, 255))
        # Left segment
        self.assertEqual(self.engine.led_frame[280], (255, 255, 0))

        # Check emitted zones for ESP32
        zones = self.transport.last_zones
        self.assertGreater(len(zones), 0)
        self.assertLessEqual(len(zones), 42, "Must not exceed ESP32 42-zone limit")

    def test_music_sync_disabled_does_not_modulate_brightness(self):
        """With Sync Music OFF, audio features do not alter brightness."""
        self.app_state.set_movie_music_sync(False)
        movie_colors = [(100, 100, 200)] * 300
        self.engine.process_movie_frame(movie_colors)

        # Feed quiet music
        self.engine.process_music_analysis(MusicAnalysis(overall=0.0, music_gate_open=False))
        time.sleep(0.10)
        bright_quiet = self.engine.led_frame[50]

        # Feed loud music
        self.engine.process_music_analysis(MusicAnalysis(overall=1.0, beat=1.0, music_gate_open=True))
        time.sleep(0.10)
        bright_loud = self.engine.led_frame[50]

        # Should be identical because Sync Music is OFF
        self.assertEqual(bright_quiet, bright_loud)

    def test_music_sync_enabled_modulates_intensity_without_changing_color(self):
        """With Sync Music ON, audio energy modulates brightness while preserving video hue."""
        self.app_state.set_movie_music_sync(True)
        # Pure blue video
        movie_colors = [(0, 0, 200)] * 300
        self.engine.process_movie_frame(movie_colors)

        # Step 1: Quiet music
        for _ in range(10):
            self.engine.process_music_analysis(MusicAnalysis(overall=0.0, beat=0.0, music_gate_open=False))
            time.sleep(0.04)
        quiet_rgb = self.engine.led_frame[50]

        # Step 2: High energy music
        for _ in range(10):
            self.engine.process_music_analysis(MusicAnalysis(overall=1.0, beat=1.0, bass_transient=1.0, music_gate_open=True))
            time.sleep(0.04)
        loud_rgb = self.engine.led_frame[50]

        # Loud should be significantly brighter than quiet
        self.assertGreater(loud_rgb[2], quiet_rgb[2])
        # Red and Green must remain 0 — color is strictly from video!
        self.assertEqual(loud_rgb[0], 0)
        self.assertEqual(loud_rgb[1], 0)
        self.assertEqual(quiet_rgb[0], 0)
        self.assertEqual(quiet_rgb[1], 0)


class TestMovieModeIntegration(unittest.TestCase):
    def setUp(self):
        self.test_config = "test_movie_integration_config.json"
        if os.path.exists(self.test_config):
            os.remove(self.test_config)
        self.app_state = AppState(self.test_config)

    def tearDown(self):
        if os.path.exists(self.test_config):
            os.remove(self.test_config)

    def test_movie_layout_persistence(self):
        """Movie layout custom counts persist across reload."""
        ok, err = self.app_state.set_movie_layout({"top": 80, "right": 70, "bottom": 80, "left": 70})
        self.assertTrue(ok)
        self.assertIsNone(err)

        layout = self.app_state.get_movie_layout()
        self.assertEqual(layout.top, 80)
        self.assertEqual(layout.right, 70)
        self.assertEqual(layout.total_leds, 300)

        # Reload from disk
        reloaded = AppState(self.test_config)
        reloaded_layout = reloaded.get_movie_layout()
        self.assertEqual(reloaded_layout.top, 80)
        self.assertEqual(reloaded_layout.right, 70)
        self.assertEqual(reloaded_layout.total_leds, 300)

    def test_movie_music_sync_persistence(self):
        """Sync music toggle persists across reload."""
        self.assertFalse(self.app_state.settings["movie"]["sync_music"])
        self.app_state.set_movie_music_sync(True)
        self.assertTrue(self.app_state.settings["movie"]["sync_music"])

        reloaded = AppState(self.test_config)
        self.assertTrue(reloaded.settings["movie"]["sync_music"])

    def test_analyzer_manager_sync_music_lifecycle(self):
        """In Movie Mode with Sync Music ON, Music Analyzer runs. With Sync Music OFF, it stops."""
        from analyzer_manager import AnalyzerManager
        transport = VirtualTransport()
        engine = LightingEngine(transport, self.app_state)
        am = AnalyzerManager(engine, self.app_state)

        # Mock start/stop to verify calls without actual hardware capture
        am.screen_analyzer.start = lambda: setattr(am.screen_analyzer, 'running', True)
        am.screen_analyzer.stop = lambda: setattr(am.screen_analyzer, 'running', False)
        am.music_analyzer.start = lambda: setattr(am.music_analyzer, 'running', True)
        am.music_analyzer.stop = lambda: setattr(am.music_analyzer, 'running', False)

        try:
            self.app_state.set_mode(AppMode.MOVIE)
            self.app_state.set_movie_music_sync(False)
            am.check_state()
            self.assertTrue(am.screen_analyzer.running)
            self.assertFalse(am.music_analyzer.running)

            # Turn Sync Music ON
            self.app_state.set_movie_music_sync(True)
            am.check_state()
            self.assertTrue(am.screen_analyzer.running)
            self.assertTrue(am.music_analyzer.running)

            # Turn Sync Music OFF
            self.app_state.set_movie_music_sync(False)
            am.check_state()
            self.assertTrue(am.screen_analyzer.running)
            self.assertFalse(am.music_analyzer.running)

            # Switch to Custom mode
            self.app_state.set_mode(AppMode.CUSTOM)
            am.check_state()
            self.assertFalse(am.screen_analyzer.running)
            self.assertFalse(am.music_analyzer.running)
        finally:
            engine.stop()


if __name__ == "__main__":
    unittest.main()

