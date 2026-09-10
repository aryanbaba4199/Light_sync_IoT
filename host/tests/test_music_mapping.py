import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from music_models import (
    LED_COUNT,
    MusicInstrument,
    ResponseEffect,
    DistributionType,
    RGBColor,
    MusicMapping,
    MusicAnalysis,
    validate_mapping,
    check_overlaps,
    generate_deterministic_leds,
    PRESETS
)
from app_state import AppState

class TestMusicModels(unittest.TestCase):
    def test_led_count_is_300(self):
        self.assertEqual(LED_COUNT, 300)

    def test_valid_mapping(self):
        m = MusicMapping(
            id="test1",
            instrument="bass",
            color=RGBColor(255, 0, 0),
            start_led=1,
            end_led=30,
            sensitivity=1.0,
            response="static",
            distribution="zone",
            enabled=True
        )
        is_valid, err = validate_mapping(m, LED_COUNT)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_invalid_start_led(self):
        m = MusicMapping(start_led=0, end_led=30)
        is_valid, err = validate_mapping(m, LED_COUNT)
        self.assertFalse(is_valid)
        self.assertIn("Start LED must be >= 1", err)

    def test_invalid_end_led(self):
        m = MusicMapping(start_led=1, end_led=400)
        is_valid, err = validate_mapping(m, LED_COUNT)
        self.assertFalse(is_valid)
        self.assertIn("End LED exceeds strip limit", err)

    def test_reversed_range(self):
        m = MusicMapping(start_led=150, end_led=50)
        is_valid, err = validate_mapping(m, LED_COUNT)
        self.assertFalse(is_valid)
        self.assertIn("must be <= End LED", err)

    def test_invalid_instrument(self):
        m = MusicMapping(instrument="synthesizer_alien")
        is_valid, err = validate_mapping(m, LED_COUNT)
        self.assertFalse(is_valid)
        self.assertIn("Unknown instrument", err)

    def test_overlap_detection(self):
        m1 = MusicMapping(id="1", instrument="bass", start_led=1, end_led=50, enabled=True)
        m2 = MusicMapping(id="2", instrument="kick", start_led=40, end_led=80, enabled=True)
        conflicts = check_overlaps([m1, m2])
        self.assertEqual(len(conflicts), 1)
        self.assertIn("overlaps with", conflicts[0])

    def test_no_overlap_adjacent(self):
        m1 = MusicMapping(id="1", instrument="bass", start_led=1, end_led=30, enabled=True)
        m2 = MusicMapping(id="2", instrument="kick", start_led=31, end_led=60, enabled=True)
        conflicts = check_overlaps([m1, m2])
        self.assertEqual(len(conflicts), 0)

    def test_disabled_mapping_ignored_in_overlap(self):
        m1 = MusicMapping(id="1", instrument="bass", start_led=1, end_led=50, enabled=True)
        m2 = MusicMapping(id="2", instrument="kick", start_led=40, end_led=80, enabled=False)
        conflicts = check_overlaps([m1, m2])
        self.assertEqual(len(conflicts), 0)

    def test_deterministic_random_assignment(self):
        # Two calls with the same seed must produce identical LED lists
        run1 = generate_deterministic_leds(1, 50, seed=12345)
        run2 = generate_deterministic_leds(1, 50, seed=12345)
        self.assertEqual(run1, run2)
        self.assertEqual(len(run1), 50)
        self.assertEqual(set(run1), set(range(0, 50)))

        # Different seed produces different ordering
        run3 = generate_deterministic_leds(1, 50, seed=99999)
        self.assertNotEqual(run1, run3)
        self.assertEqual(set(run3), set(range(0, 50)))

    def test_presets_validity(self):
        for name, preset_mappings in PRESETS.items():
            models = [MusicMapping.from_dict(m) for m in preset_mappings]
            for m in models:
                valid, err = validate_mapping(m, LED_COUNT)
                self.assertTrue(valid, f"Preset {name} has invalid mapping {m.instrument}: {err}")
            conflicts = check_overlaps(models)
            self.assertEqual(len(conflicts), 0, f"Preset {name} has unexpected overlaps: {conflicts}")

    def test_music_analysis_feature_access(self):
        analysis = MusicAnalysis(bass=0.85, kick=0.9, vocal=0.6)
        self.assertEqual(analysis.get_feature("bass"), 0.85)
        self.assertEqual(analysis.get_feature("KICK"), 0.9)
        self.assertEqual(analysis.get_feature("vocal"), 0.6)
        self.assertEqual(analysis.get_feature("nonexistent"), 0.0)

    def test_app_state_persistence_and_presets(self):
        test_file = "test_persistence.json"
        if os.path.exists(test_file):
            os.remove(test_file)
        try:
            state1 = AppState(test_file)
            self.assertEqual(state1.led_count, 300)
            self.assertEqual(len(state1.get_music_mappings()), 3)

            # Apply party preset
            state1.apply_music_preset("party")
            self.assertEqual(len(state1.get_music_mappings()), 6)

            # Reload from disk
            state2 = AppState(test_file)
            self.assertEqual(len(state2.get_music_mappings()), 6)
            self.assertEqual(state2.get_music_mappings()[0]["instrument"], "bass")
            self.assertEqual(state2.get_music_mappings()[1]["instrument"], "kick")
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

if __name__ == '__main__':
    unittest.main()
