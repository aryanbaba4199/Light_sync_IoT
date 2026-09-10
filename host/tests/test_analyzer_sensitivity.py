"""
Targeted tests for Improved Music Analyzer Sensitivity and Instrument Discrimination.
Validates:
1. Silence behavior (gate closed, features zero)
2. Constant room noise (gate closed, no spurious triggers)
3. Kick-heavy signal (kick trigger active, kick and beat response, no snare false triggers)
4. Snare transient signal (snare trigger active, no kick false triggers)
5. Hi-Hat transient signal (hihat trigger active, no kick/snare false triggers)
6. Vocal signal (vocal response active, no drum triggers)
7. Melody signal (melody response active with harmonic content)
8. Brass signal (brass response active with formant centroid)
9. Combined signals (features coexist appropriately)
"""
import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from analyzers.music_analyzer import SpectralFeatureExtractorV2
from music_models import MusicAnalysis

class TestMusicAnalyzerSensitivity(unittest.TestCase):
    def setUp(self):
        self.sample_rate = 44100
        self.chunk_size = 2048
        self.extractor = SpectralFeatureExtractorV2(sample_rate=self.sample_rate)

    def _generate_sine(self, freq: float, amplitude: float = 0.5, duration_sec: float = None):
        if duration_sec is None:
            duration_sec = self.chunk_size / self.sample_rate
        t = np.linspace(0, duration_sec, int(self.sample_rate * duration_sec), endpoint=False)
        return amplitude * np.sin(2 * np.pi * freq * t)

    def _warmup_silence(self, cycles=15):
        silence = np.zeros(self.chunk_size)
        for _ in range(cycles):
            self.extractor.extract(silence, self.sample_rate)

    def test_silence_behavior(self):
        """Silence must keep gate closed, all features zero, and no triggers."""
        silence = np.zeros(self.chunk_size)
        for _ in range(20):
            analysis = self.extractor.extract(silence, self.sample_rate)
        self.assertFalse(analysis.music_gate_open)
        self.assertEqual(analysis.kick, 0.0)
        self.assertEqual(analysis.snare, 0.0)
        self.assertEqual(analysis.hihat, 0.0)
        self.assertEqual(analysis.bass, 0.0)
        self.assertEqual(analysis.vocal, 0.0)
        self.assertEqual(analysis.melody, 0.0)
        self.assertEqual(analysis.brass, 0.0)
        self.assertFalse(analysis.kick_trigger)
        self.assertFalse(analysis.snare_trigger)
        self.assertFalse(analysis.hihat_trigger)

    def test_constant_room_noise(self):
        """Stationary background room noise must adapt noise floor and remain inactive."""
        np.random.seed(123)
        ambient = np.random.normal(0, 0.025, self.chunk_size)
        for _ in range(30):
            analysis = self.extractor.extract(ambient, self.sample_rate)
        self.assertFalse(analysis.music_gate_open)
        self.assertFalse(analysis.kick_trigger)
        self.assertFalse(analysis.snare_trigger)
        self.assertFalse(analysis.hihat_trigger)

    def test_kick_discrimination(self):
        """Kick burst (60 Hz) triggers Kick and Beat, but does not trigger Snare or HiHat."""
        self._warmup_silence()
        kick_burst = self._generate_sine(freq=60.0, amplitude=0.85)
        analysis = self.extractor.extract(kick_burst, self.sample_rate)

        self.assertTrue(analysis.music_gate_open)
        self.assertTrue(analysis.kick_trigger)
        self.assertGreater(analysis.kick, 0.6)
        self.assertGreater(analysis.beat, 0.25)
        self.assertFalse(analysis.snare_trigger)
        self.assertFalse(analysis.hihat_trigger)

    def test_snare_discrimination(self):
        """Snare burst (400 Hz) triggers Snare, but does not trigger Kick or HiHat."""
        self._warmup_silence()
        snare_burst = self._generate_sine(freq=400.0, amplitude=0.85)
        analysis = self.extractor.extract(snare_burst, self.sample_rate)

        self.assertTrue(analysis.music_gate_open)
        self.assertTrue(analysis.snare_trigger)
        self.assertGreater(analysis.snare, 0.5)
        self.assertFalse(analysis.kick_trigger)
        self.assertFalse(analysis.hihat_trigger)

    def test_hihat_discrimination(self):
        """HiHat burst (9000 Hz) triggers HiHat, but does not trigger Kick or Snare."""
        self._warmup_silence()
        hihat_burst = self._generate_sine(freq=9000.0, amplitude=0.75)
        analysis = self.extractor.extract(hihat_burst, self.sample_rate)

        self.assertTrue(analysis.music_gate_open)
        self.assertTrue(analysis.hihat_trigger)
        self.assertGreater(analysis.hihat, 0.5)
        self.assertFalse(analysis.kick_trigger)
        self.assertFalse(analysis.snare_trigger)

    def test_vocal_presence(self):
        """Vocal harmonic format (mid-range frequencies 800-1600 Hz) activates Vocal without drum false alarms."""
        self._warmup_silence()
        t = np.linspace(0, self.chunk_size/self.sample_rate, self.chunk_size, endpoint=False)
        # Formant-like composite signal: 400 Hz + 800 Hz + 1200 Hz
        vocal_sig = 0.3 * np.sin(2 * np.pi * 400 * t) + 0.35 * np.sin(2 * np.pi * 800 * t) + 0.3 * np.sin(2 * np.pi * 1200 * t)
        
        # Feed signal over several frames
        for _ in range(4):
            analysis = self.extractor.extract(vocal_sig, self.sample_rate)

        self.assertTrue(analysis.music_gate_open)
        self.assertGreater(analysis.vocal, 0.15)
        # Sustained vocal should not produce repetitive kick triggers
        self.assertFalse(analysis.kick_trigger)

    def test_melody_presence(self):
        """Pitched lead tone with harmonics activates Melody."""
        self._warmup_silence()
        t = np.linspace(0, self.chunk_size/self.sample_rate, self.chunk_size, endpoint=False)
        # Strong fundamental at 600 Hz with harmonic at 1200 Hz
        melody_sig = 0.5 * np.sin(2 * np.pi * 600 * t) + 0.25 * np.sin(2 * np.pi * 1200 * t)
        for _ in range(4):
            analysis = self.extractor.extract(melody_sig, self.sample_rate)

        self.assertTrue(analysis.music_gate_open)
        self.assertGreater(analysis.melody, 0.10)

    def test_brass_presence(self):
        """Horn formant (1800 Hz centroid) activates Brass."""
        self._warmup_silence()
        brass_sig = self._generate_sine(freq=1800.0, amplitude=0.8)
        for _ in range(4):
            analysis = self.extractor.extract(brass_sig, self.sample_rate)

        self.assertTrue(analysis.music_gate_open)
        self.assertGreater(analysis.brass, 0.10)

    def test_dense_audio_coexistence(self):
        """Dense music with both low and high elements allows features to coexist."""
        self._warmup_silence()
        t = np.linspace(0, self.chunk_size/self.sample_rate, self.chunk_size, endpoint=False)
        # 80 Hz bass + 800 Hz vocal + 8000 Hz hat
        dense_sig = 0.4 * np.sin(2 * np.pi * 80 * t) + 0.3 * np.sin(2 * np.pi * 800 * t) + 0.25 * np.sin(2 * np.pi * 8000 * t)
        for _ in range(5):
            analysis = self.extractor.extract(dense_sig, self.sample_rate)

        self.assertTrue(analysis.music_gate_open)
        self.assertGreater(analysis.overall, 0.3)
        self.assertGreater(analysis.bass, 0.1)

if __name__ == '__main__':
    unittest.main()
