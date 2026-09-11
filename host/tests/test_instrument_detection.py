import unittest
import numpy as np
import time

from analyzers.music_analyzer import SpectralFeatureExtractorV2
from music_models import MusicAnalysis, MusicMapping, RGBColor, LED_COUNT
from music_mapping_engine import MusicMappingEngine

class TestInstrumentDetection(unittest.TestCase):
    def setUp(self):
        self.sample_rate = 44100
        self.chunk_size = 2048
        self.extractor = SpectralFeatureExtractorV2(sample_rate=self.sample_rate)

    def _warmup_silence(self, frames=15):
        silence = np.zeros(self.chunk_size, dtype=np.float32)
        for _ in range(frames):
            self.extractor.extract(silence, self.sample_rate)

    def _generate_sine(self, freq: float, amplitude: float = 0.8) -> np.ndarray:
        t = np.arange(self.chunk_size) / float(self.sample_rate)
        return (amplitude * np.sin(2.0 * np.pi * freq * t)).astype(np.float32)

    def _generate_harmonic_vocal(self, f0: float = 220.0, amplitude: float = 0.75) -> np.ndarray:
        """Generates a voiced vowel tone with distinct harmonic formants at f0, 2*f0, 3*f0, 4*f0, 5*f0."""
        t = np.arange(self.chunk_size) / float(self.sample_rate)
        harmonics = [
            (f0 * 1, 0.40),  # Fundamental (220 Hz)
            (f0 * 2, 0.35),  # F1 formant (440 Hz)
            (f0 * 3, 0.25),  # 660 Hz
            (f0 * 4, 0.20),  # F2 formant (880 Hz)
            (f0 * 5, 0.15),  # 1100 Hz
            (f0 * 6, 0.10),  # 1320 Hz
        ]
        sig = np.zeros(self.chunk_size, dtype=np.float32)
        for freq, weight in harmonics:
            sig += weight * np.sin(2.0 * np.pi * freq * t)
        sig = sig / np.max(np.abs(sig)) * amplitude
        return sig.astype(np.float32)

    def _generate_broadband_clap(self, amplitude: float = 0.85) -> np.ndarray:
        """Generates a broadband mid-frequency noise burst (1200-4000 Hz) simulating a hand clap."""
        rng = np.random.RandomState(42)
        noise = rng.randn(self.chunk_size).astype(np.float32)
        # Bandpass filter between 1200 and 4500 Hz
        import scipy.signal
        b, a = scipy.signal.butter(3, [1200.0 / (self.sample_rate / 2.0), 4500.0 / (self.sample_rate / 2.0)], btype='band')
        filtered = scipy.signal.lfilter(b, a, noise)
        filtered = filtered / np.max(np.abs(filtered)) * amplitude
        return filtered.astype(np.float32)

    # -------------------------------------------------------------------------
    # 1. KICK VS BASS SEPARATION
    # -------------------------------------------------------------------------
    def test_kick_transient_onset_produces_event(self):
        """A sudden short low-frequency burst triggers a kick event."""
        self._warmup_silence()
        kick_hit = self._generate_sine(freq=65.0, amplitude=0.85)
        analysis = self.extractor.extract(kick_hit, self.sample_rate)

        self.assertTrue(analysis.music_gate_open)
        self.assertTrue(analysis.kick_trigger)
        self.assertGreater(analysis.kick, 0.5)

    def test_sustained_bass_does_not_repeatedly_trigger_kick(self):
        """A sustained low-frequency bass tone does NOT continuously re-trigger kick on every frame."""
        self._warmup_silence()
        bass_tone = self._generate_sine(freq=60.0, amplitude=0.80)

        # Frame 1: Initial onset hit
        a1 = self.extractor.extract(bass_tone, self.sample_rate)
        # Frame 1 may trigger kick on the initial onset
        time.sleep(0.02)

        # Frames 2-6: Sustained tone continues without new transients
        kick_triggers_during_sustain = 0
        for _ in range(5):
            time.sleep(0.01)
            a = self.extractor.extract(bass_tone, self.sample_rate)
            if a.kick_trigger:
                kick_triggers_during_sustain += 1

        # Kick must NOT keep triggering on sustained low-frequency sound
        self.assertEqual(kick_triggers_during_sustain, 0, "Kick must not repeatedly trigger during sustained bass")

    def test_sustained_bass_maintains_high_envelope_level(self):
        """Sustained low frequency signal produces a sustained bass level, behaving as an envelope."""
        self._warmup_silence()
        bass_tone = self._generate_sine(freq=70.0, amplitude=0.80)

        # Feed 4 consecutive frames of sustained bass
        last_analysis = None
        for _ in range(4):
            time.sleep(0.01)
            last_analysis = self.extractor.extract(bass_tone, self.sample_rate)

        self.assertTrue(last_analysis.music_gate_open)
        self.assertGreater(last_analysis.bass, 0.35, "Bass must remain active during sustained low-frequency energy")

    def test_kick_and_bass_coexist_independently(self):
        """Kick is an event while bass is an envelope level; both coexist with separate signals."""
        self._warmup_silence()
        sub_tone = self._generate_sine(freq=60.0, amplitude=0.85)

        # Frame 1: Hit
        a = self.extractor.extract(sub_tone, self.sample_rate)
        self.assertTrue(a.kick_trigger)
        self.assertGreater(a.bass, 0.0)

        # Frame 2: Decay of kick event, but sustain of bass
        time.sleep(0.15) # Wait past kick decay
        a2 = self.extractor.extract(sub_tone, self.sample_rate)
        self.assertFalse(a2.kick_trigger)
        self.assertGreater(a2.bass, 0.20)

    # -------------------------------------------------------------------------
    # 2. CLAP VS HI-HAT
    # -------------------------------------------------------------------------
    def test_clap_detection_on_broadband_transient(self):
        """Broadband mid-frequency burst triggers a Clap response."""
        self._warmup_silence()
        clap_burst = self._generate_broadband_clap(amplitude=0.85)
        analysis = self.extractor.extract(clap_burst, self.sample_rate)

        self.assertTrue(analysis.music_gate_open)
        self.assertTrue(analysis.clap_trigger)
        self.assertGreater(analysis.clap, 0.4)
        # Backward compatibility alias
        self.assertTrue(analysis.snare_trigger)
        self.assertGreater(analysis.snare, 0.4)

    def test_hihat_transient_favors_hihat_over_clap(self):
        """High-frequency transient (>7000 Hz) favors Hi-Hat and suppresses Clap."""
        self._warmup_silence()
        hihat_burst = self._generate_sine(freq=8500.0, amplitude=0.85)
        analysis = self.extractor.extract(hihat_burst, self.sample_rate)

        self.assertTrue(analysis.music_gate_open)
        self.assertTrue(analysis.hihat_trigger)
        self.assertGreater(analysis.hihat, 0.4)
        self.assertFalse(analysis.clap_trigger, "Hi-Hat must not falsely trigger Clap")

    def test_mid_broadband_favors_clap_over_hihat(self):
        """Mid-frequency clap burst triggers Clap, not Hi-Hat."""
        self._warmup_silence()
        clap_burst = self._generate_broadband_clap(amplitude=0.85)
        analysis = self.extractor.extract(clap_burst, self.sample_rate)

        self.assertTrue(analysis.clap_trigger)
        self.assertFalse(analysis.hihat_trigger, "Clap must not falsely trigger Hi-Hat")

    # -------------------------------------------------------------------------
    # 3. ADVANCED HARMONIC VOCAL DETECTION
    # -------------------------------------------------------------------------
    def test_vocal_candidate_on_harmonic_singing_tone(self):
        """Sustained harmonic tone in speech/singing formant range produces vocal activation."""
        self._warmup_silence()
        vocal_sig = self._generate_harmonic_vocal(f0=240.0, amplitude=0.80)

        # Feed 3 consecutive frames to allow vocal envelope to smoothly rise
        last_analysis = None
        for _ in range(3):
            time.sleep(0.01)
            last_analysis = self.extractor.extract(vocal_sig, self.sample_rate)

        self.assertTrue(last_analysis.music_gate_open)
        self.assertGreater(last_analysis.vocal, 0.20, "Harmonic voice must activate vocal detector")

    def test_kick_transient_does_not_falsely_classify_as_vocal(self):
        """Deep low-frequency kick transient does not falsely trigger vocal."""
        self._warmup_silence()
        kick_burst = self._generate_sine(freq=55.0, amplitude=0.90)
        analysis = self.extractor.extract(kick_burst, self.sample_rate)

        self.assertTrue(analysis.kick_trigger)
        self.assertLess(analysis.vocal, 0.10, "Kick must not bleed into vocal detection")

    def test_vocal_smooth_attack_and_decay(self):
        """Vocal output decays smoothly during silence and does not rapidly flicker."""
        self._warmup_silence()
        vocal_sig = self._generate_harmonic_vocal(f0=220.0, amplitude=0.85)

        # Activate vocal
        for _ in range(4):
            time.sleep(0.01)
            self.extractor.extract(vocal_sig, self.sample_rate)

        vocal_peak = self.extractor.smooth_features["vocal"]
        self.assertGreater(vocal_peak, 0.20)

        # Silence frame: vocal should sustain/hold and decay smoothly, not immediately drop to 0
        silence = np.zeros(self.chunk_size, dtype=np.float32)
        # Note: if master gate closes it clears, so we test with low background noise to test vocal decay
        bg_noise = (np.random.RandomState(1).randn(self.chunk_size) * 0.02).astype(np.float32)
        time.sleep(0.05)
        a_decay = self.extractor.extract(bg_noise, self.sample_rate)
        # Verify that vocal value is non-zero during hold/smooth decay
        self.assertGreater(a_decay.vocal, 0.05, "Vocal should decay smoothly without instant clicking to 0")

    def test_vocal_detected_during_active_song_mix(self):
        """Vocal formant harmonics are detected even when accompanied by low-frequency kick and bass."""
        self._warmup_silence()
        vocal_sig = self._generate_harmonic_vocal(f0=240.0, amplitude=0.60)
        kick_burst = self._generate_sine(freq=60.0, amplitude=0.50)
        bass_sig = self._generate_sine(freq=90.0, amplitude=0.30)
        song_mix = (vocal_sig + kick_burst + bass_sig) * 0.70

        # Feed 4 consecutive frames
        last_analysis = None
        for _ in range(4):
            time.sleep(0.01)
            last_analysis = self.extractor.extract(song_mix, self.sample_rate)

        self.assertTrue(last_analysis.music_gate_open)
        self.assertGreater(last_analysis.vocal, 0.15, "Vocal must be detected in realistic song mix with drums and bass")

    # -------------------------------------------------------------------------
    # 4. LED OUTPUT VERIFICATION
    # -------------------------------------------------------------------------
    def test_mapping_engine_renders_frame_with_all_instruments(self):
        """MusicMappingEngine renders a 300-LED frame from analysis containing clap, kick, bass, vocal."""
        engine = MusicMappingEngine(led_count=LED_COUNT)
        mappings = [
            MusicMapping(id="m1", instrument="bass", color=RGBColor(255, 0, 0), start_led=1, end_led=50),
            MusicMapping(id="m2", instrument="kick", color=RGBColor(255, 100, 0), start_led=51, end_led=100),
            MusicMapping(id="m3", instrument="clap", color=RGBColor(255, 200, 0), start_led=101, end_led=150),
            MusicMapping(id="m4", instrument="vocal", color=RGBColor(180, 0, 255), start_led=151, end_led=200),
            MusicMapping(id="m5", instrument="hihat", color=RGBColor(0, 200, 255), start_led=201, end_led=250),
            MusicMapping(id="m6", instrument="melody", color=RGBColor(0, 255, 100), start_led=251, end_led=300),
        ]

        analysis = MusicAnalysis(
            bass=0.7,
            kick=0.9,
            clap=0.8,
            vocal=0.75,
            hihat=0.6,
            melody=0.5,
            kick_trigger=True,
            clap_trigger=True,
            hihat_trigger=True,
            music_gate_open=True
        )

        # Render in FLASH mode
        frame_flash = engine.render_frame(analysis, mappings, response_mode="flash")
        self.assertEqual(len(frame_flash), LED_COUNT)
        # Kick zone (51-100) must be flashing (active)
        self.assertNotEqual(frame_flash[60], (0, 0, 0))
        # Clap zone (101-150) must be flashing (active)
        self.assertNotEqual(frame_flash[110], (0, 0, 0))

        # Render in FADE mode
        frame_fade = engine.render_frame(analysis, mappings, response_mode="fade")
        self.assertEqual(len(frame_fade), LED_COUNT)
        self.assertNotEqual(frame_fade[20], (0, 0, 0)) # Bass zone
        self.assertNotEqual(frame_fade[170], (0, 0, 0)) # Vocal zone

if __name__ == '__main__':
    unittest.main()
