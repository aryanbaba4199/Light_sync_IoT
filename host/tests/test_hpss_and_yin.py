"""
Unit & Integration Tests for Real-Time HPSS (Harmonic-Percussive Source Separation)
and YIN Real-Time Vocal Pitch Tracking in DevLights Music Analyzer.
"""
import sys
import os
import time
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from analyzers.music_analyzer import (
    YINPitchTracker,
    RealtimeHPSS,
    SpectralFeatureExtractorV2
)
from music_models import MusicAnalysis, MusicMapping, RGBColor
from music_mapping_engine import MusicMappingEngine


class TestYINPitchTracker(unittest.TestCase):
    def setUp(self):
        self.sample_rate = 44100
        self.chunk_size = 2048
        self.yin = YINPitchTracker(sample_rate=self.sample_rate)

    def _generate_tone(self, freq: float, amplitude: float = 0.8) -> np.ndarray:
        t = np.arange(self.chunk_size) / float(self.sample_rate)
        # Fundamental plus 2nd harmonic (typical of vocal cord vibration)
        sig = 0.7 * np.sin(2.0 * np.pi * freq * t) + 0.3 * np.sin(2.0 * np.pi * 2.0 * freq * t)
        return (sig * amplitude).astype(np.float32)

    def test_yin_detects_standard_vocal_pitches(self):
        """YIN must accurately detect male and female singing voice fundamental frequencies."""
        test_frequencies = [120.0, 180.0, 240.0, 320.0, 400.0]
        for f in test_frequencies:
            tone = self._generate_tone(f, amplitude=0.8)
            pitch, confidence = self.yin.compute_pitch(tone, self.sample_rate)
            self.assertGreater(confidence, 0.80, f"Pitch confidence too low for {f} Hz: {confidence}")
            self.assertAlmostEqual(pitch, f, delta=f * 0.03, msg=f"Detected pitch {pitch} Hz drifted from target {f} Hz")

    def test_yin_rejects_unvoiced_noise(self):
        """Broadband random noise (unvoiced) must have low confidence."""
        rng = np.random.RandomState(42)
        noise = (rng.randn(self.chunk_size) * 0.4).astype(np.float32)
        pitch, confidence = self.yin.compute_pitch(noise, self.sample_rate)
        self.assertLess(confidence, 0.35, f"Noise should have low confidence, got {confidence}")

    def test_yin_handles_silence_gracefully(self):
        """Zero / low amplitude signal returns 0.0 pitch and 0.0 confidence immediately."""
        silence = np.zeros(self.chunk_size, dtype=np.float32)
        pitch, confidence = self.yin.compute_pitch(silence, self.sample_rate)
        self.assertEqual(pitch, 0.0)
        self.assertEqual(confidence, 0.0)

    def test_yin_execution_time_is_sub_millisecond(self):
        """YIN pitch tracking must execute in under 1.0 ms to support 60 FPS real-time processing."""
        tone = self._generate_tone(220.0)
        # Warmup
        self.yin.compute_pitch(tone, self.sample_rate)

        start = time.perf_counter()
        iterations = 50
        for _ in range(iterations):
            self.yin.compute_pitch(tone, self.sample_rate)
        elapsed_ms = (time.perf_counter() - start) / iterations * 1000.0

        self.assertLess(elapsed_ms, 1.0, f"YIN execution time {elapsed_ms:.3f} ms exceeds 1.0 ms budget")


class TestRealtimeHPSS(unittest.TestCase):
    def setUp(self):
        self.n_bins = 1025
        self.hpss = RealtimeHPSS(n_bins=self.n_bins, n_frames=7, l_harm=5, l_perc=15)

    def test_hpss_sustained_tone_is_harmonic(self):
        """A tone sustained over consecutive frames must be separated into the harmonic stream."""
        tone_frame = np.zeros(self.n_bins, dtype=np.float32)
        tone_frame[99:102] = 20.0

        for _ in range(5):
            mag_h, mag_p, ratio = self.hpss.update(tone_frame)

        self.assertGreater(ratio, 0.80, f"Sustained tone should have high harmonic ratio, got {ratio}")
        self.assertGreater(np.sum(mag_h), np.sum(mag_p) * 4.0, "Harmonic energy must dominate percussive energy")

    def test_hpss_isolated_transient_is_percussive(self):
        """A sudden 1-frame broadband burst after silence must be separated into the percussive stream."""
        silence = np.zeros(self.n_bins, dtype=np.float32)
        for _ in range(6):
            self.hpss.update(silence)

        drum_frame = np.zeros(self.n_bins, dtype=np.float32)
        drum_frame[20:400] = 10.0

        mag_h, mag_p, ratio = self.hpss.update(drum_frame)
        self.assertLess(ratio, 0.20, f"Drum transient should have low harmonic ratio, got {ratio}")
        self.assertGreater(np.sum(mag_p), np.sum(mag_h) * 4.0, "Percussive energy must dominate harmonic energy")

    def test_hpss_execution_time_is_under_two_milliseconds(self):
        """HPSS update must execute in under 2.0 ms per frame."""
        frame = np.random.rand(self.n_bins).astype(np.float32)
        self.hpss.update(frame)

        start = time.perf_counter()
        iterations = 50
        for _ in range(iterations):
            self.hpss.update(frame)
        elapsed_ms = (time.perf_counter() - start) / iterations * 1000.0

        self.assertLess(elapsed_ms, 2.0, f"HPSS execution time {elapsed_ms:.3f} ms exceeds 2.0 ms budget")


class TestEndToEndMIRFeatureExtraction(unittest.TestCase):
    def setUp(self):
        self.sample_rate = 44100
        self.chunk_size = 2048
        self.extractor = SpectralFeatureExtractorV2(sample_rate=self.sample_rate)

    def _warmup_silence(self, frames=15):
        silence = np.zeros(self.chunk_size, dtype=np.float32)
        for _ in range(frames):
            self.extractor.extract(silence, self.sample_rate)

    def _generate_vocal(self, f0: float = 240.0, amplitude: float = 0.8) -> np.ndarray:
        t = np.arange(self.chunk_size) / float(self.sample_rate)
        harmonics = [
            (f0 * 1, 0.40),
            (f0 * 2, 0.35),
            (f0 * 3, 0.25),
            (f0 * 4, 0.20),
            (f0 * 5, 0.15),
            (f0 * 6, 0.10),
        ]
        sig = np.zeros(self.chunk_size, dtype=np.float32)
        for freq, weight in harmonics:
            sig += weight * np.sin(2.0 * np.pi * freq * t)
        return (sig / np.max(np.abs(sig)) * amplitude).astype(np.float32)

    def _generate_kick(self, amplitude: float = 0.8) -> np.ndarray:
        t = np.arange(self.chunk_size) / float(self.sample_rate)
        return (amplitude * np.sin(2.0 * np.pi * 60.0 * t)).astype(np.float32)

    def test_vocal_alone_populates_pitch_and_confidence(self):
        """Sustained singing tone populates vocal_pitch and high vocal_confidence."""
        self._warmup_silence()
        vocal = self._generate_vocal(f0=240.0, amplitude=0.85)

        last_analysis = None
        for _ in range(4):
            time.sleep(0.01)
            last_analysis = self.extractor.extract(vocal, self.sample_rate)

        self.assertTrue(last_analysis.music_gate_open)
        self.assertGreater(last_analysis.vocal, 0.20)
        self.assertAlmostEqual(last_analysis.vocal_pitch, 240.0, delta=10.0)
        self.assertGreater(last_analysis.vocal_confidence, 0.70)
        self.assertGreater(last_analysis.harmonic_ratio, 0.60)

    def test_vocal_in_dense_mix_remains_active(self):
        """Vocal remains detected when played simultaneously with a heavy 60 Hz kick drum and 90 Hz bass."""
        self._warmup_silence()
        vocal = self._generate_vocal(f0=240.0, amplitude=0.60)
        kick = self._generate_kick(amplitude=0.50)
        t = np.arange(self.chunk_size) / float(self.sample_rate)
        bass = (0.35 * np.sin(2.0 * np.pi * 90.0 * t)).astype(np.float32)

        dense_mix = (vocal + kick + bass) * 0.70

        last_analysis = None
        for _ in range(4):
            time.sleep(0.01)
            last_analysis = self.extractor.extract(dense_mix, self.sample_rate)

        self.assertTrue(last_analysis.music_gate_open)
        self.assertGreater(last_analysis.vocal, 0.15, "Vocal must not be extinguished by drums/bass")
        self.assertGreater(last_analysis.vocal_confidence, 0.50)
        self.assertAlmostEqual(last_analysis.vocal_pitch, 240.0, delta=15.0)

    def test_drums_alone_do_not_falsely_trigger_vocal(self):
        """Pure drum kicks and percussion do not produce false vocal trigger."""
        self._warmup_silence()
        kick = self._generate_kick(amplitude=0.90)
        analysis = self.extractor.extract(kick, self.sample_rate)

        self.assertTrue(analysis.kick_trigger)
        self.assertLess(analysis.vocal, 0.10, "Kick must not trigger vocal")

    def test_analysis_serialization_contains_mir_fields(self):
        """MusicAnalysis.to_dict() must include vocal_pitch, vocal_confidence, and harmonic_ratio."""
        analysis = MusicAnalysis(
            bass=0.7,
            vocal=0.85,
            vocal_pitch=220.5,
            vocal_confidence=0.92,
            harmonic_ratio=0.88
        )
        d = analysis.to_dict()
        self.assertIn("vocal_pitch", d)
        self.assertIn("vocal_confidence", d)
        self.assertIn("harmonic_ratio", d)
        self.assertEqual(d["vocal_pitch"], 220.5)
        self.assertEqual(d["vocal_confidence"], 0.92)
        self.assertEqual(d["harmonic_ratio"], 0.88)


if __name__ == '__main__':
    unittest.main()
