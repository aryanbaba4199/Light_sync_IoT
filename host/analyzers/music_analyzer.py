"""
Audio Analyzer & Feature Extraction for DevLights.

Extracts 9 normalized audio features (0.0 to 1.0) using spectral FFT analysis,
onset transient flux, and band energy estimation:
- Bass: Low-frequency sub energy (20–150 Hz)
- Kick: Low-frequency transient onset detection
- Snare: Mid/high transient impact energy (250–1500 Hz)
- Vocal: Speech & singing formant energy (300–3000 Hz)
- HiHat: High-frequency cymbal & shimmer energy (5000–16000 Hz)
- Brass: Warm harmonic richness in the mid-range (500–3500 Hz)
- Melody: Dominant melodic pitch prominence in mid-high spectrum
- Beat: Broadband transient spectral flux
- Overall: Root-Mean-Square (RMS) normalized energy

Designed with a modular FeatureExtractor interface so ML models
can be plugged in seamlessly in the future.
"""
import time
import threading
import logging
import numpy as np
import sounddevice as sd
import scipy.fftpack

from music_models import MusicAnalysis

logger = logging.getLogger("MusicAnalyzer")

class BaseFeatureExtractor:
    """Interface for audio feature extraction (heuristic or ML-based)."""
    def extract(self, audio_data: np.ndarray, sample_rate: int) -> MusicAnalysis:
        raise NotImplementedError

class SpectralFeatureExtractor(BaseFeatureExtractor):
    """
    Real-time spectral and transient feature estimator based on FFT,
    spectral flux, peak prominence, and formant estimation.
    """
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        
        # Attack and release smoothing rates
        self.attack = 0.65
        self.release = 0.15

        # Feature smoothed states
        self.smooth_features = {
            "bass": 0.0,
            "kick": 0.0,
            "snare": 0.0,
            "vocal": 0.0,
            "hihat": 0.0,
            "brass": 0.0,
            "melody": 0.0,
            "beat": 0.0,
            "overall": 0.0
        }

        # Transient detection memory
        self.prev_bass_energy = 0.0
        self.prev_mid_energy = 0.0
        self.prev_spectrum = None

    def extract(self, audio_data: np.ndarray, sample_rate: int) -> MusicAnalysis:
        # Calculate RMS energy
        rms = np.sqrt(np.mean(np.square(audio_data)))
        raw_overall = min(1.0, float(rms * 8.0))

        # Quiet threshold gating
        if rms < 0.001:
            for k in self.smooth_features:
                self.smooth_features[k] *= 0.7
            return MusicAnalysis(**{k: float(v) for k, v in self.smooth_features.items()})

        # Apply Hanning window
        window = np.hanning(len(audio_data))
        windowed = audio_data * window
        
        # FFT computation
        fft_complex = scipy.fftpack.fft(windowed)
        fft_mag = np.abs(fft_complex)
        freqs = scipy.fftpack.fftfreq(len(fft_complex), 1.0 / sample_rate)

        # Positive frequencies only
        pos_mask = freqs > 0
        mag = fft_mag[pos_mask]
        f = freqs[pos_mask]

        if len(mag) == 0:
            return MusicAnalysis()

        # 1. BASS (20 - 150 Hz)
        bass_mask = (f >= 20) & (f <= 150)
        raw_bass_energy = float(np.mean(mag[bass_mask])) if np.any(bass_mask) else 0.0
        raw_bass = min(1.0, raw_bass_energy * 0.025)

        # 2. KICK (Low-frequency transient onset)
        # Difference in bass energy above running average indicates a kick impact
        bass_delta = max(0.0, raw_bass_energy - self.prev_bass_energy)
        self.prev_bass_energy = self.prev_bass_energy * 0.7 + raw_bass_energy * 0.3
        raw_kick = min(1.0, bass_delta * 0.06)

        # 3. SNARE (Transient mid-energy spike 250 - 1500 Hz)
        snare_mask = (f >= 250) & (f <= 1500)
        snare_energy = float(np.mean(mag[snare_mask])) if np.any(snare_mask) else 0.0
        snare_delta = max(0.0, snare_energy - self.prev_mid_energy)
        self.prev_mid_energy = self.prev_mid_energy * 0.8 + snare_energy * 0.2
        raw_snare = min(1.0, snare_delta * 0.08)

        # 4. VOCAL (Formant energy 300 - 3000 Hz)
        vocal_mask = (f >= 300) & (f <= 3000)
        raw_vocal_energy = float(np.mean(mag[vocal_mask])) if np.any(vocal_mask) else 0.0
        raw_vocal = min(1.0, raw_vocal_energy * 0.035)

        # 5. HI-HAT (High-frequency sizzle 5000 - 16000 Hz)
        hihat_mask = (f >= 5000) & (f <= 16000)
        raw_hihat_energy = float(np.mean(mag[hihat_mask])) if np.any(hihat_mask) else 0.0
        raw_hihat = min(1.0, raw_hihat_energy * 0.07)

        # 6. BRASS (Harmonic content in 500 - 3500 Hz with higher centroid)
        brass_mask = (f >= 500) & (f <= 3500)
        if np.any(brass_mask):
            brass_mag = mag[brass_mask]
            brass_f = f[brass_mask]
            total_mag = np.sum(brass_mag)
            centroid = np.sum(brass_f * brass_mag) / (total_mag + 1e-6)
            # Centroid around 1500-2500Hz indicates brass presence
            centroid_factor = 1.0 if 1200 <= centroid <= 2800 else 0.6
            raw_brass = min(1.0, (np.mean(brass_mag) * 0.03) * centroid_factor)
        else:
            raw_brass = 0.0

        # 7. MELODY (Peak prominence in 400 - 4000 Hz)
        melody_mask = (f >= 400) & (f <= 4000)
        if np.any(melody_mask):
            melody_mag = mag[melody_mask]
            peak_val = np.max(melody_mag)
            mean_val = np.mean(melody_mag) + 1e-6
            peak_ratio = peak_val / mean_val
            raw_melody = min(1.0, (peak_ratio - 1.0) * 0.25)
        else:
            raw_melody = 0.0

        # 8. BEAT (Broadband spectral flux)
        if self.prev_spectrum is not None and len(self.prev_spectrum) == len(mag):
            flux = np.sum(np.maximum(0.0, mag - self.prev_spectrum))
            raw_beat = min(1.0, float(flux * 0.00015))
        else:
            raw_beat = raw_kick
        self.prev_spectrum = mag.copy()

        raw_dict = {
            "bass": raw_bass,
            "kick": raw_kick,
            "snare": raw_snare,
            "vocal": raw_vocal,
            "hihat": raw_hihat,
            "brass": raw_brass,
            "melody": raw_melody,
            "beat": raw_beat,
            "overall": raw_overall
        }

        # Apply asymmetric attack / release smoothing
        for k, raw_val in raw_dict.items():
            prev = self.smooth_features[k]
            rate = self.attack if raw_val > prev else self.release
            self.smooth_features[k] = prev * (1.0 - rate) + raw_val * rate

        return MusicAnalysis(
            bass=float(self.smooth_features["bass"]),
            kick=float(self.smooth_features["kick"]),
            snare=float(self.smooth_features["snare"]),
            vocal=float(self.smooth_features["vocal"]),
            hihat=float(self.smooth_features["hihat"]),
            brass=float(self.smooth_features["brass"]),
            melody=float(self.smooth_features["melody"]),
            beat=float(self.smooth_features["beat"]),
            overall=float(self.smooth_features["overall"])
        )

class MusicAnalyzer:
    """
    Main audio capture service. Opens microphone / Core Audio stream
    and publishes MusicAnalysis objects to the lighting engine.
    """
    def __init__(self, lighting_engine, extractor: BaseFeatureExtractor = None):
        self.engine = lighting_engine
        self.extractor = extractor or SpectralFeatureExtractor()
        
        self.running = False
        self.thread = None
        self.status = "stopped"
        
        self.sample_rate = 44100
        self.chunk_size = 2048  # approx 46ms analysis frames (~22 Hz)
        self.latest_analysis = MusicAnalysis()

    def start(self):
        if self.running:
            return
        self.running = True
        self.status = "starting"
        self.thread = threading.Thread(target=self._analyze_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.status = "stopped"
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            self.thread = None

    def _analyze_loop(self):
        try:
            # Query default input device
            dev_info = sd.query_devices(kind='input')
            if not dev_info:
                self.status = "no_device"
                logger.error("No audio input device found.")
                return

            logger.info(f"Opening audio stream on: {dev_info.get('name')}")

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                blocksize=self.chunk_size,
                dtype='float32'
            ) as stream:
                self.status = "running"
                
                while self.running:
                    data, overflowed = stream.read(self.chunk_size)
                    if overflowed:
                        pass # Ignore buffer overflows gracefully
                    
                    audio_data = data[:, 0]
                    analysis = self.extractor.extract(audio_data, self.sample_rate)
                    self.latest_analysis = analysis

                    # Pass analysis to the lighting engine
                    if self.engine:
                        if hasattr(self.engine, "process_music_analysis"):
                            self.engine.process_music_analysis(analysis)
                        else:
                            # Fallback to single ambient color
                            r = int(analysis.bass * 255)
                            g = int(analysis.vocal * 255)
                            b = int(analysis.hihat * 255)
                            self.engine.set_ambient_color(r, g, b)
                            self.engine.set_ambient_brightness(analysis.overall)

        except sd.PortAudioError as e:
            msg = str(e).lower()
            if "permission" in msg or "not authorized" in msg:
                self.status = "permission_denied"
            else:
                self.status = f"portaudio_error: {str(e)}"
            logger.error(f"PortAudio error in MusicAnalyzer: {e}")
            self.running = False
        except Exception as e:
            self.status = f"error: {str(e)}"
            logger.error(f"Error in MusicAnalyzer: {e}")
            self.running = False
