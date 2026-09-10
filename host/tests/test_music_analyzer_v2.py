"""
Unit tests for Audio Analysis V2 in DevLights.
Validates:
- HysteresisGate (Schmitt trigger)
- AdaptiveNoiseFloor (Asymmetric leaky integration)
- TransientDetector (Onset detection & refractory periods)
- TransientEnvelope (Attack-Hold-Decay state machine)
- SpectralFeatureExtractorV2 (Noise rejection, low-cut filter, transient onsets, master gate)
- Dual-Mode Bass response in MusicMappingEngine (Sustained vs Flash transient)
"""
import sys
import os
import time
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from analyzers.music_analyzer import (
    HysteresisGate,
    AdaptiveNoiseFloor,
    TransientDetector,
    TransientEnvelope,
    SpectralFeatureExtractorV2
)
from music_models import MusicAnalysis, MusicMapping, RGBColor
from music_mapping_engine import MusicMappingEngine


class TestHysteresisGate(unittest.TestCase):
    def test_schmitt_trigger_behavior(self):
        gate = HysteresisGate(open_thresh=0.25, close_thresh=0.15)
        self.assertFalse(gate.is_open)

        # Signal below open threshold - remains closed
        self.assertFalse(gate.update(0.10))
        self.assertFalse(gate.update(0.24))

        # Reaches open threshold - opens
        self.assertTrue(gate.update(0.25))
        self.assertTrue(gate.is_open)

        # Drops between open and close thresholds - stays open (hysteresis band)
        self.assertTrue(gate.update(0.20))
        self.assertTrue(gate.update(0.16))

        # Drops below close threshold - closes
        self.assertFalse(gate.update(0.14))
        self.assertFalse(gate.is_open)

        # Rises back into dead zone - stays closed until open threshold
        self.assertFalse(gate.update(0.20))
        self.assertTrue(gate.update(0.26))


class TestAdaptiveNoiseFloor(unittest.TestCase):
    def test_asymmetric_adaptation(self):
        # alpha_down > alpha_up ensures rapid falloff when silent, slow creep during sounds
        tracker = AdaptiveNoiseFloor(alpha_up=0.01, alpha_down=0.20, margin=1.20)

        # Seed floor
        excess = tracker.update("band1", 10.0)
        self.assertEqual(excess, 0.0)
        self.assertEqual(tracker.get_floor("band1"), 10.0)

        # Value drops to 2.0 -> adapts downward quickly (alpha_down = 0.20)
        tracker.update("band1", 2.0)
        floor_after_drop = tracker.get_floor("band1")
        # 10.0 * 0.8 + 2.0 * 0.2 = 8.4
        self.assertAlmostEqual(floor_after_drop, 8.4, places=2)

        # Value rises to 15.0 -> creeps upward very slowly (alpha_up = 0.01)
        tracker.update("band1", 15.0)
        floor_after_rise = tracker.get_floor("band1")
        # 8.4 * 0.99 + 15.0 * 0.01 = 8.466
        self.assertAlmostEqual(floor_after_rise, 8.466, places=2)

    def test_steady_noise_settles_to_zero_excess(self):
        tracker = AdaptiveNoiseFloor(alpha_up=0.10, alpha_down=0.10, margin=1.20)
        tracker.update("rms", 5.0)

        # Feed steady 5.0 noise for several cycles
        for _ in range(30):
            excess = tracker.update("rms", 5.0)

        # Since value (5.0) is less than floor * margin (5.0 * 1.20 = 6.0), excess must be 0.0
        self.assertEqual(excess, 0.0)


class TestTransientDetector(unittest.TestCase):
    def test_onset_and_refractory_period(self):
        detector = TransientDetector(min_energy=1.0, min_rise=0.8, refractory_sec=0.100)
        now = 100.0

        # Quiet background
        trig, intensity = detector.process(0.2, now)
        self.assertFalse(trig)

        # Sudden strong onset (rise > 0.8 and energy > 1.0)
        now += 0.020
        trig, intensity = detector.process(3.0, now)
        self.assertTrue(trig)
        self.assertGreater(intensity, 0.5)

        # Consecutive frame immediately after (now + 0.020s < refractory 0.100s)
        now += 0.020
        trig, intensity = detector.process(3.5, now)
        self.assertFalse(trig, "Should NOT trigger within refractory cooldown")

        # After refractory period elapses (now + 0.120s)
        now += 0.120
        trig, intensity = detector.process(4.0, now)
        self.assertTrue(trig, "Should trigger after refractory cooldown elapses")


class TestTransientEnvelope(unittest.TestCase):
    def test_attack_hold_decay_cycle(self):
        env = TransientEnvelope(hold_sec=0.040, decay_sec=0.100)
        t = 100.0

        # Trigger attack
        env.trigger(intensity=1.0, now=t)
        self.assertAlmostEqual(env.current_val, 1.0)

        # During hold (t + 0.020s < 0.040s)
        t += 0.020
        val = env.update(now=t)
        self.assertAlmostEqual(val, 1.0, msg="Should hold full intensity")

        # Past hold period -> decay starts
        t += 0.030  # t is now 100.050s (> 100.040s)
        val = env.update(now=t)
        self.assertLess(val, 1.0, msg="Should start decaying")

        # Progress through decay
        for _ in range(10):
            t += 0.020
            val = env.update(now=t)

        # Should cleanly settle to 0.0
        t += 0.200
        val = env.update(now=t)
        self.assertEqual(val, 0.0)


class TestSpectralFeatureExtractorV2(unittest.TestCase):
    def setUp(self):
        self.sample_rate = 44100
        self.chunk_size = 2048
        self.extractor = SpectralFeatureExtractorV2(sample_rate=self.sample_rate)

    def _generate_sine(self, freq: float, amplitude: float = 0.5, duration_sec: float = None):
        if duration_sec is None:
            duration_sec = self.chunk_size / self.sample_rate
        t = np.linspace(0, duration_sec, int(self.sample_rate * duration_sec), endpoint=False)
        return amplitude * np.sin(2 * np.pi * freq * t)

    def test_low_cut_filter_rejects_sub_40hz_rumble(self):
        """25 Hz rumble (fan/desk vibration) should be eliminated by the low-cut filter."""
        # Warm up extractor noise floor with low rumble
        rumble = self._generate_sine(freq=25.0, amplitude=0.4)
        for _ in range(30):
            analysis = self.extractor.extract(rumble, self.sample_rate)

        # Bass and kick specifically must be 0.0 because 25 Hz < 40 Hz filter cut
        self.assertEqual(analysis.bass, 0.0)
        self.assertEqual(analysis.kick, 0.0)
        self.assertFalse(analysis.kick_trigger)

    def test_ambient_noise_rejection_settles_to_zero(self):
        """Steady stationary noise should adapt noise floor and close master activity gate."""
        np.random.seed(42)
        # Constant low-amplitude ambient noise (RMS ~ 0.03)
        ambient = np.random.normal(0, 0.03, self.chunk_size)

        for _ in range(30):
            analysis = self.extractor.extract(ambient, self.sample_rate)

        # After noise floor adapts to the stationary noise, master gate should close
        # and all features should settle to 0.0
        self.assertFalse(analysis.music_gate_open)
        self.assertEqual(analysis.kick, 0.0)
        self.assertEqual(analysis.snare, 0.0)
        self.assertEqual(analysis.hihat, 0.0)
        self.assertEqual(analysis.bass, 0.0)
        self.assertEqual(analysis.melody, 0.0)

    def test_kick_transient_onset(self):
        """Sudden burst in 60 Hz band triggers Kick with instant attack."""
        # Establish low quiet baseline
        silence = np.zeros(self.chunk_size)
        for _ in range(15):
            self.extractor.extract(silence, self.sample_rate)

        # Sudden high-amplitude 60 Hz kick hit
        kick_burst = self._generate_sine(freq=60.0, amplitude=0.8)
        analysis = self.extractor.extract(kick_burst, self.sample_rate)

        self.assertTrue(analysis.music_gate_open)
        self.assertTrue(analysis.kick_trigger)
        self.assertGreater(analysis.kick, 0.5)

    def test_snare_transient_onset(self):
        """Sudden burst in 400 Hz band triggers Snare onset."""
        silence = np.zeros(self.chunk_size)
        for _ in range(15):
            self.extractor.extract(silence, self.sample_rate)

        snare_burst = self._generate_sine(freq=400.0, amplitude=0.8)
        analysis = self.extractor.extract(snare_burst, self.sample_rate)

        self.assertTrue(analysis.music_gate_open)
        self.assertTrue(analysis.snare_trigger)
        self.assertGreater(analysis.snare, 0.4)

    def test_hihat_transient_onset(self):
        """Sudden high-frequency burst (8000 Hz) triggers Hi-Hat onset."""
        silence = np.zeros(self.chunk_size)
        for _ in range(15):
            self.extractor.extract(silence, self.sample_rate)

        hihat_burst = self._generate_sine(freq=8000.0, amplitude=0.8)
        analysis = self.extractor.extract(hihat_burst, self.sample_rate)

        self.assertTrue(analysis.music_gate_open)
        self.assertTrue(analysis.hihat_trigger)
        self.assertGreater(analysis.hihat, 0.4)


class TestDualModeBassMapping(unittest.TestCase):
    def test_bass_smooth_vs_flash_response(self):
        engine = MusicMappingEngine(led_count=300)

        # Mapping 1: Bass with sustained ('static') response
        mapping_sustained = [
            MusicMapping(
                id="bass_sustained",
                instrument="bass",
                color=RGBColor(255, 0, 0),
                start_led=1,
                end_led=100,
                sensitivity=1.0,
                response="static"
            )
        ]

        # Analysis where sustained bass is high (0.8), but transient is 0.0 (middle of sustained note)
        analysis = MusicAnalysis(
            bass=0.8,
            bass_transient=0.0,
            music_gate_open=True
        )

        zones = engine.extract_zones_for_protocol(analysis, mapping_sustained)
        self.assertEqual(len(zones), 1)
        # Sustained mode should use sustained bass (0.8 -> brightness ~ 204)
        self.assertAlmostEqual(zones[0]["r"], int(255 * 0.8), delta=5)

        # Mapping 2: Bass with 'flash' response
        mapping_flash = [
            MusicMapping(
                id="bass_flash",
                instrument="bass",
                color=RGBColor(255, 0, 0),
                start_led=1,
                end_led=100,
                sensitivity=1.0,
                response="flash"
            )
        ]

        # When bass_transient is 0.0, flash mode should produce 0 brightness
        zones_flash_off = engine.extract_zones_for_protocol(analysis, mapping_flash)
        self.assertEqual(zones_flash_off[0]["r"], 0)

        # When bass_transient fires (1.0), flash mode lights up
        analysis_attack = MusicAnalysis(
            bass=0.8,
            bass_transient=1.0,
            music_gate_open=True
        )
        zones_flash_on = engine.extract_zones_for_protocol(analysis_attack, mapping_flash)
        self.assertEqual(zones_flash_on[0]["r"], 255)


if __name__ == '__main__':
    unittest.main()
