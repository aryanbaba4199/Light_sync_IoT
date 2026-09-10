import sys
import os
import math
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from custom_effects import CustomEffectEngine, DEFAULT_EFFECT_CONFIGS, LED_COUNT
from app_state import AppState


class TestCustomEffects(unittest.TestCase):
    def setUp(self):
        self.engine = CustomEffectEngine(led_count=300)

    # -------------------------------------------------------------------------
    # 1. Rainfall Tests
    # -------------------------------------------------------------------------
    def test_rainfall_bounce_and_trail(self):
        config = {
            "color": {"r": 0, "g": 120, "b": 255},
            "speed": 50,
            "active_led_count": 10,
            "trail_length": 10
        }
        
        # Test forward motion (t = 0.5s)
        frame_fwd = self.engine.render("rainfall", config, 300, elapsed_time=0.5, dt=0.033)
        self.assertEqual(len(frame_fwd), 300)
        active_fwd = [i for i, c in enumerate(frame_fwd) if c != (0, 0, 0)]
        self.assertLessEqual(len(active_fwd), 10)
        self.assertGreater(len(active_fwd), 0)

        # Verify gradient trail monotonically decreases from head to tail
        active_colors = [frame_fwd[i] for i in active_fwd]
        brightnesses = [max(c) for c in active_colors]
        # In forward motion, higher index is head, lower index is tail
        self.assertEqual(brightnesses, sorted(brightnesses))

        # Test bounce backward motion at cycle midpoint
        # Cycle length is 2 * (300 - 1) = 598. At speed 50 (leds_per_sec = 60), 598 / 60 ≈ 9.96s
        # Midpoint ~ 5.5s should be moving backward
        frame_bwd = self.engine.render("rainfall", config, 300, elapsed_time=5.5, dt=0.033)
        self.assertEqual(len(frame_bwd), 300)
        active_bwd = [i for i, c in enumerate(frame_bwd) if c != (0, 0, 0)]
        self.assertLessEqual(len(active_bwd), 10)
        self.assertGreater(len(active_bwd), 0)

    # -------------------------------------------------------------------------
    # 2. Flash Tests
    # -------------------------------------------------------------------------
    def test_flash_square_wave_and_stability(self):
        config = {
            "color": {"r": 255, "g": 255, "b": 255},
            "color_mode": "random",
            "speed": 50  # cycle ~ 0.5s, ON for 0.25s, OFF for 0.25s
        }
        
        # In ON phase (e.g. t = 0.05s)
        frame_on = self.engine.render("flash", config, 300, elapsed_time=0.05, dt=0.033)
        self.assertNotEqual(frame_on[0], (0, 0, 0))
        # Uniform color across all 300 LEDs
        self.assertTrue(all(c == frame_on[0] for c in frame_on))

        # Same flash cycle at t = 0.15s should preserve the EXACT same random color
        frame_on_later = self.engine.render("flash", config, 300, elapsed_time=0.15, dt=0.033)
        self.assertEqual(frame_on[0], frame_on_later[0])

        # In OFF phase (e.g. t = 0.35s)
        frame_off = self.engine.render("flash", config, 300, elapsed_time=0.35, dt=0.033)
        self.assertTrue(all(c == (0, 0, 0) for c in frame_off))

    # -------------------------------------------------------------------------
    # 3. Random Effect Tests
    # -------------------------------------------------------------------------
    def test_random_positions_and_stability(self):
        config = {
            "active_led_count": 20,
            "color_mode": "random",
            "speed": 30,  # interval ~ 1.4s
            "fade": False
        }
        
        # Frame at t = 0.1s
        frame_1 = self.engine.render("random", config, 300, elapsed_time=0.1, dt=0.033)
        active_1 = [i for i, c in enumerate(frame_1) if c != (0, 0, 0)]
        self.assertLessEqual(len(active_1), 20)
        self.assertGreater(len(active_1), 0)

        # Frame at t = 0.3s (within same interval) should have the exact same positions
        frame_2 = self.engine.render("random", config, 300, elapsed_time=0.3, dt=0.033)
        active_2 = [i for i, c in enumerate(frame_2) if c != (0, 0, 0)]
        self.assertEqual(active_1, active_2)

    # -------------------------------------------------------------------------
    # 4. Wave, Comet, Breathing, Sparkle, Color Chase, Fire, Rainbow Tests
    # -------------------------------------------------------------------------
    def test_wave_renders_valid_range(self):
        config = DEFAULT_EFFECT_CONFIGS["wave"]
        frame = self.engine.render("wave", config, 300, elapsed_time=1.0, dt=0.033)
        self.assertEqual(len(frame), 300)
        for r, g, b in frame:
            self.assertTrue(0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255)

    def test_comet_renders_valid_range(self):
        config = DEFAULT_EFFECT_CONFIGS["comet"]
        frame = self.engine.render("comet", config, 300, elapsed_time=1.0, dt=0.033)
        self.assertEqual(len(frame), 300)
        active = [c for c in frame if c != (0, 0, 0)]
        self.assertGreater(len(active), 0)

    def test_breathing_uniform_pulse(self):
        config = {"color": {"r": 200, "g": 100, "b": 50}, "speed": 40, "min_brightness": 0.1, "max_brightness": 1.0}
        frame = self.engine.render("breathing", config, 300, elapsed_time=1.0, dt=0.033)
        self.assertEqual(len(frame), 300)
        self.assertTrue(all(c == frame[0] for c in frame))

    def test_sparkle_renders_valid_range(self):
        config = DEFAULT_EFFECT_CONFIGS["sparkle"]
        frame = self.engine.render("sparkle", config, 300, elapsed_time=1.0, dt=0.033)
        self.assertEqual(len(frame), 300)
        self.assertTrue(any(c != (0, 0, 0) for c in frame))

    def test_color_chase_renders_valid_range(self):
        config = DEFAULT_EFFECT_CONFIGS["color_chase"]
        frame = self.engine.render("color_chase", config, 300, elapsed_time=1.0, dt=0.033)
        self.assertEqual(len(frame), 300)

    def test_fire_renders_valid_range(self):
        config = DEFAULT_EFFECT_CONFIGS["fire"]
        for step in range(10):
            frame = self.engine.render("fire", config, 300, elapsed_time=step * 0.033, dt=0.033)
        self.assertEqual(len(frame), 300)
        for r, g, b in frame:
            self.assertTrue(0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255)

    def test_rainbow_flow_renders_spectrum(self):
        config = DEFAULT_EFFECT_CONFIGS["rainbow_flow"]
        frame = self.engine.render("rainbow_flow", config, 300, elapsed_time=0.5, dt=0.033)
        self.assertEqual(len(frame), 300)
        unique_colors = len(set(frame))
        self.assertGreater(unique_colors, 20)

    # -------------------------------------------------------------------------
    # 5. Global Brightness and Power Gating
    # -------------------------------------------------------------------------
    def test_power_gating_produces_black(self):
        config = DEFAULT_EFFECT_CONFIGS["rainbow_flow"]
        frame = self.engine.render("rainbow_flow", config, 300, elapsed_time=1.0, dt=0.033, power_on=False)
        self.assertTrue(all(c == (0, 0, 0) for c in frame))

    def test_global_brightness_scaling(self):
        config = {"color": {"r": 200, "g": 100, "b": 50}, "speed": 30, "min_brightness": 1.0, "max_brightness": 1.0}
        frame_full = self.engine.render("breathing", config, 300, elapsed_time=0.0, dt=0.033, global_brightness=1.0)
        frame_half = self.engine.render("breathing", config, 300, elapsed_time=0.0, dt=0.033, global_brightness=0.5)
        
        for (r1, g1, b1), (r2, g2, b2) in zip(frame_full, frame_half):
            self.assertAlmostEqual(r1 * 0.5, r2, delta=2)
            self.assertAlmostEqual(g1 * 0.5, g2, delta=2)
            self.assertAlmostEqual(b1 * 0.5, b2, delta=2)

    # -------------------------------------------------------------------------
    # 6. Protocol V2 Zone Limits (<= 42 zones)
    # -------------------------------------------------------------------------
    def test_all_effects_enforce_zone_limit_42(self):
        effects = [
            "rainfall", "flash", "random", "wave", "comet",
            "breathing", "sparkle", "color_chase", "fire", "rainbow_flow"
        ]
        
        for eff in effects:
            cfg = DEFAULT_EFFECT_CONFIGS[eff]
            frame = self.engine.render(eff, cfg, 300, elapsed_time=1.5, dt=0.033)
            zones = self.engine.extract_zones_for_protocol(frame, eff, cfg)
            
            self.assertLessEqual(
                len(zones), 42,
                f"Effect '{eff}' produced {len(zones)} zones, exceeding ESP32 limit of 42!"
            )
            for z in zones:
                self.assertIn("start", z)
                self.assertIn("end", z)
                self.assertIn("r", z)
                self.assertIn("g", z)
                self.assertIn("b", z)
                self.assertTrue(0 <= z["start"] <= z["end"] < 300)


class TestAppStateCustomIntegration(unittest.TestCase):
    def test_app_state_custom_methods(self):
        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp.close()
        try:
            state = AppState(config_file=tmp.name)
            
            # Default should be rainfall
            self.assertEqual(state.get_custom_effect(), "rainfall")
            self.assertIn("speed", state.get_custom_config("rainfall"))
            
            # Change effect to wave
            self.assertTrue(state.set_custom_effect("wave"))
            self.assertEqual(state.get_custom_effect(), "wave")
            
            # Update wave config
            ok, err = state.set_custom_config("wave", {"speed": 80, "width": 45})
            self.assertTrue(ok)
            self.assertIsNone(err)
            cfg = state.get_custom_config("wave")
            self.assertEqual(cfg["speed"], 80)
            self.assertEqual(cfg["width"], 45)
            
            # Re-read from disk to ensure persistence
            state2 = AppState(config_file=tmp.name)
            self.assertEqual(state2.get_custom_effect(), "wave")
            self.assertEqual(state2.get_custom_config("wave")["speed"], 80)
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)


if __name__ == '__main__':
    unittest.main()
