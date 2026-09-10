import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from music_models import MusicAnalysis, MusicMapping, RGBColor, LED_COUNT
from music_mapping_engine import MusicMappingEngine

class TestMusicMappingEngine(unittest.TestCase):
    def setUp(self):
        self.engine = MusicMappingEngine(led_count=300)

    def test_zero_intensity_results_in_black(self):
        mapping = MusicMapping(
            id="m1",
            instrument="bass",
            color=RGBColor(255, 0, 0),
            start_led=1,
            end_led=30,
            response="static"
        )
        analysis = MusicAnalysis(bass=0.0)
        frame = self.engine.render_frame(analysis, [mapping])
        
        # Check zone LEDs (0 to 29)
        for i in range(30):
            self.assertEqual(frame[i], (0, 0, 0))

    def test_max_intensity_zone(self):
        mapping = MusicMapping(
            id="m1",
            instrument="bass",
            color=RGBColor(255, 100, 50),
            start_led=1,
            end_led=30,
            sensitivity=1.0,
            response="static"
        )
        analysis = MusicAnalysis(bass=1.0)
        frame = self.engine.render_frame(analysis, [mapping], user_brightness=1.0, mode_limit=1.0)
        
        # LEDs 1-30 (index 0 to 29) should be fully lit
        for i in range(30):
            self.assertEqual(frame[i], (255, 100, 50))
        # LEDs 31-300 should be off
        for i in range(30, 300):
            self.assertEqual(frame[i], (0, 0, 0))

    def test_sensitivity_scaling_and_clamping(self):
        mapping = MusicMapping(
            id="m1",
            instrument="bass",
            color=RGBColor(200, 100, 0),
            start_led=1,
            end_led=10,
            sensitivity=2.0,
            response="static"
        )
        # 0.4 feature * 2.0 sensitivity = 0.8 intensity
        analysis = MusicAnalysis(bass=0.4)
        frame = self.engine.render_frame(analysis, [mapping], user_brightness=1.0, mode_limit=1.0)
        
        expected_r = int(200 * 0.8) # 160
        expected_g = int(100 * 0.8) # 80
        self.assertEqual(frame[0], (expected_r, expected_g, 0))

        # Test over-saturation clamp: 0.8 * 2.0 = 1.6 -> clamped to 1.0
        analysis_high = MusicAnalysis(bass=0.8)
        frame_high = self.engine.render_frame(analysis_high, [mapping], user_brightness=1.0, mode_limit=1.0)
        self.assertEqual(frame_high[0], (200, 100, 0))

    def test_multi_instrument_zone_isolation(self):
        bass_map = MusicMapping(id="b", instrument="bass", color=RGBColor(255, 0, 0), start_led=1, end_led=30, response="static")
        kick_map = MusicMapping(id="k", instrument="kick", color=RGBColor(255, 120, 0), start_led=31, end_led=60, response="static")
        vocal_map = MusicMapping(id="v", instrument="vocal", color=RGBColor(180, 0, 255), start_led=61, end_led=130, response="static")

        analysis = MusicAnalysis(bass=1.0, kick=0.5, vocal=0.8)
        frame = self.engine.render_frame(analysis, [bass_map, kick_map, vocal_map])

        # Bass section: LEDs 1–30
        for i in range(0, 30):
            self.assertEqual(frame[i], (255, 0, 0))
        # Kick section: LEDs 31–60 (intensity 0.5)
        for i in range(30, 60):
            self.assertEqual(frame[i], (int(255 * 0.5), int(120 * 0.5), 0))
        # Vocal section: LEDs 61–130 (intensity 0.8)
        for i in range(60, 130):
            self.assertEqual(frame[i], (int(180 * 0.8), 0, int(255 * 0.8)))
        # Unassigned: LEDs 131–300
        for i in range(130, 300):
            self.assertEqual(frame[i], (0, 0, 0))

    def test_power_off_forces_all_black(self):
        bass_map = MusicMapping(id="b", instrument="bass", color=RGBColor(255, 255, 255), start_led=1, end_led=300, response="static")
        analysis = MusicAnalysis(bass=1.0)
        frame = self.engine.render_frame(analysis, [bass_map], power_on=False)
        for i in range(300):
            self.assertEqual(frame[i], (0, 0, 0))

    def test_brightness_pipeline_applied_once(self):
        mapping = MusicMapping(id="b", instrument="bass", color=RGBColor(100, 100, 100), start_led=1, end_led=10, response="static")
        analysis = MusicAnalysis(bass=1.0) # feature = 1.0
        # user_brightness = 0.5, mode_limit = 0.8 -> combined = 0.4
        frame = self.engine.render_frame(analysis, [mapping], user_brightness=0.5, mode_limit=0.8)
        self.assertEqual(frame[0], (40, 40, 40))

    def test_random_distribution_stability(self):
        mapping = MusicMapping(
            id="rand1",
            instrument="bass",
            color=RGBColor(255, 0, 0),
            start_led=1,
            end_led=50,
            distribution="random",
            response="static",
            seed=42
        )
        analysis = MusicAnalysis(bass=1.0)
        frame1 = self.engine.render_frame(analysis, [mapping])
        frame2 = self.engine.render_frame(analysis, [mapping])

        # Verify exact stability between frame 1 and frame 2
        self.assertEqual(frame1, frame2)

        # Count active LEDs: exactly 50 LEDs must be lit
        active_indices = [i for i in range(300) if frame1[i] == (255, 0, 0)]
        self.assertEqual(len(active_indices), 50)
        self.assertTrue(all(0 <= idx < 50 for idx in active_indices))

if __name__ == '__main__':
    unittest.main()
