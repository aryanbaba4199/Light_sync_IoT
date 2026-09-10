"""
Audio Analyzer & Feature Extraction V2 for DevLights.

Features:
- Low-cut filter (< 40 Hz) to eliminate desk vibrations and mechanical AC/fan rumble.
- Adaptive Per-Band & Master Noise Floor estimation with asymmetric leaky integration.
- Master Musical Activity Gate (Schmitt trigger / hysteresis).
- Transient onset detectors for Kick (40–120 Hz), Snare (250–1500 Hz), and Hi-Hat (5500–16000 Hz)
  with refractory cooldown periods to prevent double triggers.
- Reusable Attack-Hold-Decay envelope generators for punchy visual flashes.
- Dual-mode Bass: sustained musical energy for smooth/pulse, transient onset energy for flash.
- Melody harmonic prominence in 400–4000 Hz with local spectral normalization and hysteresis.
- Vocal speech/singing formant concentration with noise gating.
- Native audio sample rate detection from sounddevice input device.
- Live telemetry metrics published to Diagnostics.
"""
import time
import threading
import logging
from typing import Tuple, Dict
import numpy as np
import sounddevice as sd
import scipy.fftpack
import scipy.signal

from music_models import MusicAnalysis

logger = logging.getLogger("MusicAnalyzer")

class HysteresisGate:
    """Schmitt trigger to prevent rapid flickering around a threshold."""
    def __init__(self, open_thresh: float = 0.25, close_thresh: float = 0.15):
        self.open_thresh = open_thresh
        self.close_thresh = close_thresh
        self.is_open = False

    def update(self, value: float) -> bool:
        if self.is_open:
            if value < self.close_thresh:
                self.is_open = False
        else:
            if value >= self.open_thresh:
                self.is_open = True
        return self.is_open

class AdaptiveNoiseFloor:
    """
    Asymmetric leaky integrator for per-band and overall noise floor tracking.
    Adapts downward quickly when quiet; creeps upward smoothly to track ambient noise floors.
    """
    def __init__(self, alpha_up: float = 0.035, alpha_down: float = 0.05, margin: float = 1.25):
        self.alpha_up = alpha_up
        self.alpha_down = alpha_down
        self.margin = margin
        self.floors: Dict[str, float] = {
            "rms": 0.005,
            "bass": 0.5,
            "kick": 0.5,
            "snare": 0.5,
            "hihat": 0.1,
            "vocal": 0.5,
            "brass": 0.5,
            "melody": 0.5,
        }

    def update(self, key: str, value: float, custom_margin: float = None) -> float:
        m = custom_margin if custom_margin is not None else self.margin
        if key not in self.floors:
            self.floors[key] = max(0.001, float(value))
            return 0.0

        floor = self.floors[key]
        if value < floor:
            floor = floor * (1.0 - self.alpha_down) + value * self.alpha_down
        else:
            floor = floor * (1.0 - self.alpha_up) + value * self.alpha_up
        self.floors[key] = floor

        # Return positive signal above the noise floor margin
        return max(0.0, float(value - floor * m))

    def get_floor(self, key: str) -> float:
        return self.floors.get(key, 0.0)

class TransientDetector:
    """
    Detects dynamic onsets (rapid positive energy rise over running background).
    Enforces a refractory cooldown period to prevent multiple triggers from one hit.
    """
    def __init__(self, min_energy: float = 1.0, min_rise: float = 0.8, refractory_sec: float = 0.080):
        self.min_energy = min_energy
        self.min_rise = min_rise
        self.refractory_sec = refractory_sec
        self.running_avg = 0.0
        self.last_trigger_time = 0.0

    def process(self, energy: float, now: float) -> Tuple[bool, float]:
        rise = max(0.0, float(energy - self.running_avg))
        self.running_avg = self.running_avg * 0.70 + energy * 0.30

        time_since = now - self.last_trigger_time
        if (energy >= self.min_energy and 
            rise >= self.min_rise and 
            time_since >= self.refractory_sec):
            
            self.last_trigger_time = now
            intensity = min(1.0, max(0.5, rise / (self.min_rise * 2.0)))
            return True, intensity
        return False, 0.0

class TransientEnvelope:
    """
    Attack-Hold-Decay envelope generator.
    Produces an instant attack, holds for visual impact, then decays cleanly to 0.
    """
    def __init__(self, hold_sec: float = 0.040, decay_sec: float = 0.140):
        self.hold_sec = hold_sec
        self.decay_sec = decay_sec
        self.current_val = 0.0
        self.hold_until = 0.0
        self.last_time = time.time()

    def trigger(self, intensity: float = 1.0, now: float = None):
        if now is None:
            now = time.time()
        self.current_val = max(self.current_val, min(1.0, float(intensity)))
        self.hold_until = now + self.hold_sec

    def update(self, now: float = None) -> float:
        if now is None:
            now = time.time()
        dt = max(0.001, min(0.1, now - self.last_time))
        self.last_time = now

        if now < self.hold_until:
            return self.current_val

        # Exponential decay
        decay_factor = max(0.0, 1.0 - (dt / self.decay_sec))
        self.current_val *= decay_factor
        if self.current_val < 0.015:
            self.current_val = 0.0
        return self.current_val

    def clear(self):
        self.current_val = 0.0
        self.hold_until = 0.0

class BaseFeatureExtractor:
    """Interface for audio feature extraction."""
    def extract(self, audio_data: np.ndarray, sample_rate: int) -> MusicAnalysis:
        raise NotImplementedError

class SpectralFeatureExtractorV2(BaseFeatureExtractor):
    """
    Audio Analysis Engine V2:
    - Low-cut rumble filter (< 40 Hz)
    - Adaptive Noise Floor subtraction with tuned musical sensitivity
    - Master Musical Activity Gate
    - Transient Onset + Attack-Hold-Decay for Kick, Snare, HiHat
    - Dual-mode Bass (Sustained + Flash transient)
    - Melody harmonic peak prominence with Hysteresis
    - Vocal speech formant concentration with noise gating
    - Brass spectral centroid and harmonic focus
    - Beat weighted rhythmic combination
    - Overall musical energy representation
    """
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

        # Noise Floor Trackers (Tuned margins: 1.20-1.25)
        self.noise_tracker = AdaptiveNoiseFloor(alpha_up=0.035, alpha_down=0.05, margin=1.25)

        # Master Activity Gate (Hysteresis)
        self.music_gate = HysteresisGate(open_thresh=0.015, close_thresh=0.008)

        # Transient Onset Detectors (Tuned for ~80-85% responsiveness)
        self.kick_detector = TransientDetector(min_energy=0.68, min_rise=0.45, refractory_sec=0.085)
        self.snare_detector = TransientDetector(min_energy=1.05, min_rise=0.62, refractory_sec=0.090)
        self.hihat_detector = TransientDetector(min_energy=0.26, min_rise=0.20, refractory_sec=0.065)
        self.bass_transient_detector = TransientDetector(min_energy=0.68, min_rise=0.45, refractory_sec=0.085)

        # Attack-Hold-Decay Envelopes for Drum Transients
        self.kick_env = TransientEnvelope(hold_sec=0.040, decay_sec=0.130)
        self.snare_env = TransientEnvelope(hold_sec=0.035, decay_sec=0.140)
        self.hihat_env = TransientEnvelope(hold_sec=0.018, decay_sec=0.085)
        self.bass_transient_env = TransientEnvelope(hold_sec=0.040, decay_sec=0.130)

        # Hysteresis Gates for Sustained Features
        self.melody_gate = HysteresisGate(open_thresh=0.22, close_thresh=0.12)
        self.vocal_gate = HysteresisGate(open_thresh=0.18, close_thresh=0.10)

        # Smooth memory for sustained features
        self.smooth_features = {
            "bass": 0.0,
            "vocal": 0.0,
            "brass": 0.0,
            "melody": 0.0,
            "beat": 0.0,
            "overall": 0.0
        }

        self.prev_spectrum = None
        self.last_debug_log_time = 0.0

    def extract(self, audio_data: np.ndarray, sample_rate: int) -> MusicAnalysis:
        now = time.time()
        self.sample_rate = sample_rate

        # 1. High-Pass Filter (< 45 Hz) to eliminate desk vibrations and mechanical rumble
        if not hasattr(self, '_hp_filter_sr') or self._hp_filter_sr != sample_rate:
            self._hp_filter_sr = sample_rate
            self._hp_b, self._hp_a = scipy.signal.butter(4, 45.0 / (sample_rate / 2.0), btype='high')
        filtered_audio = scipy.signal.lfilter(self._hp_b, self._hp_a, audio_data)

        # 2. Root-Mean-Square (RMS) Energy on filtered signal
        rms = float(np.sqrt(np.mean(np.square(filtered_audio))))
        effective_rms = self.noise_tracker.update("rms", rms, custom_margin=1.25)
        is_music_active = self.music_gate.update(effective_rms)

        # 3. FFT Computation with Hanning Window (always run to maintain spectral noise floor tracking)
        window = np.hanning(len(filtered_audio))
        windowed = filtered_audio * window
        fft_complex = scipy.fftpack.fft(windowed)
        fft_mag = np.abs(fft_complex)
        freqs = scipy.fftpack.fftfreq(len(fft_complex), 1.0 / sample_rate)

        # Positive frequencies only
        pos_mask = freqs > 0
        mag = fft_mag[pos_mask]
        f = freqs[pos_mask]

        if len(mag) == 0:
            return MusicAnalysis()

        # 4. Low-Cut Mask (<= 45 Hz)
        low_cut_mask = f <= 45.0
        mag[low_cut_mask] = 0.0

        # 5. Extract Raw Band Energies & Update Adaptive Noise Floors
        # Bass: 45–150 Hz (Noise margin 1.40 preserves rejection of low-end leakage)
        bass_mask = (f >= 45) & (f <= 150)
        raw_bass = float(np.mean(mag[bass_mask])) if np.any(bass_mask) else 0.0
        eff_bass = self.noise_tracker.update("bass", raw_bass, custom_margin=1.40)

        # Kick: 45–120 Hz (Tuned margin 1.25 for quick transient reaction)
        kick_mask = (f >= 45) & (f <= 120)
        raw_kick = float(np.mean(mag[kick_mask])) if np.any(kick_mask) else 0.0
        eff_kick = self.noise_tracker.update("kick", raw_kick, custom_margin=1.25)

        # Snare: 250–1500 Hz (Tuned margin 1.22)
        snare_mask = (f >= 250) & (f <= 1500)
        raw_snare = float(np.mean(mag[snare_mask])) if np.any(snare_mask) else 0.0
        eff_snare = self.noise_tracker.update("snare", raw_snare, custom_margin=1.22)

        # Hi-Hat: 5500–16000 Hz (Tuned margin 1.20)
        hihat_mask = (f >= 5500) & (f <= 16000)
        raw_hihat = float(np.mean(mag[hihat_mask])) if np.any(hihat_mask) else 0.0
        eff_hihat = self.noise_tracker.update("hihat", raw_hihat, custom_margin=1.20)

        # Vocal: 300–3200 Hz (Tuned margin 1.22)
        vocal_mask = (f >= 300) & (f <= 3200)
        raw_vocal = float(np.mean(mag[vocal_mask])) if np.any(vocal_mask) else 0.0
        eff_vocal = self.noise_tracker.update("vocal", raw_vocal, custom_margin=1.22)

        # Brass: 500–3500 Hz (Tuned margin 1.22)
        brass_mask = (f >= 500) & (f <= 3500)
        raw_brass = float(np.mean(mag[brass_mask])) if np.any(brass_mask) else 0.0
        eff_brass = self.noise_tracker.update("brass", raw_brass, custom_margin=1.22)

        # Melody: 400–4000 Hz (Tuned margin 1.22)
        melody_mask = (f >= 400) & (f <= 4000)
        raw_melody = float(np.mean(mag[melody_mask])) if np.any(melody_mask) else 0.0
        eff_melody = self.noise_tracker.update("melody", raw_melody, custom_margin=1.22)

        # 6. Master Gate Closed (Silence or Constant Ambient Noise)
        if not is_music_active:
            for k in self.smooth_features:
                self.smooth_features[k] *= 0.6
                if self.smooth_features[k] < 0.005:
                    self.smooth_features[k] = 0.0

            # Clear transient envelopes when gate is closed
            self.kick_env.clear()
            self.snare_env.clear()
            self.hihat_env.clear()
            self.bass_transient_env.clear()

            self._publish_diagnostics(is_gate_open=False, kick_trig=False, snare_trig=False, hihat_trig=False)
            return MusicAnalysis(
                bass=float(self.smooth_features["bass"]),
                kick=float(self.kick_env.current_val),
                snare=float(self.snare_env.current_val),
                vocal=float(self.smooth_features["vocal"]),
                hihat=float(self.hihat_env.current_val),
                brass=float(self.smooth_features["brass"]),
                melody=float(self.smooth_features["melody"]),
                beat=float(self.smooth_features["beat"]),
                overall=float(self.smooth_features["overall"]),
                kick_trigger=False,
                snare_trigger=False,
                hihat_trigger=False,
                music_gate_open=False,
                bass_transient=float(self.bass_transient_env.current_val)
            )

        # 7. Music Active -> Extract Features & Detect Transients
        # Bass
        sustained_bass = min(1.0, max(0.0, (eff_bass - 0.45) * 0.20))
        bass_trig, bass_trig_int = self.bass_transient_detector.process(eff_bass, now)
        if bass_trig:
            self.bass_transient_env.trigger(bass_trig_int, now)
        bass_transient_val = self.bass_transient_env.update(now)

        # Kick: must have genuine low-end dominance over snare band
        kick_trig, kick_int = self.kick_detector.process(eff_kick, now)
        # Suppress kick trigger if snare energy vastly exceeds kick energy (e.g. sharp mid snare hit)
        if kick_trig and (eff_snare > eff_kick * 2.2):
            kick_trig = False
            kick_int = 0.0
        if kick_trig:
            self.kick_env.trigger(kick_int, now)
        kick_val = self.kick_env.update(now)

        # Snare
        snare_trig, snare_int = self.snare_detector.process(eff_snare, now)
        if snare_trig:
            self.snare_env.trigger(snare_int, now)
        snare_val = self.snare_env.update(now)

        # Hi-Hat
        hihat_trig, hihat_int = self.hihat_detector.process(eff_hihat, now)
        if hihat_trig:
            self.hihat_env.trigger(hihat_int, now)
        hihat_val = self.hihat_env.update(now)

        # Vocal: Speech and singing formant presence with spectral concentration
        # Uses mid-range energy with improved normalization
        broadband_mask = (f >= 60) & (f <= 16000)
        broadband_energy = float(np.mean(mag[broadband_mask])) if np.any(broadband_mask) else 1e-6
        vocal_ratio = raw_vocal / (broadband_energy + 1e-6)
        # Check that energy isn't solely concentrated in deep sub-bass (< 120 Hz)
        low_energy = float(np.mean(mag[(f >= 45) & (f <= 150)])) if np.any(bass_mask) else 0.0
        vocal_weight = 1.0 if raw_vocal >= low_energy * 0.25 else 0.5
        vocal_candidate = min(1.0, max(0.0, (eff_vocal - 0.55) * 0.19 * vocal_weight))
        vocal_val = vocal_candidate if self.vocal_gate.update(vocal_candidate) else 0.0

        # Brass: Spectral centroid focus in horn formant range (1200-2800 Hz)
        if np.any(brass_mask):
            brass_mag = mag[brass_mask]
            brass_f = f[brass_mask]
            total_m = np.sum(brass_mag)
            centroid = np.sum(brass_f * brass_mag) / (total_m + 1e-6)
            c_factor = 1.0 if (1200 <= centroid <= 2800) else 0.5
            brass_val = min(1.0, max(0.0, eff_brass * 0.075 * c_factor))
        else:
            brass_val = 0.0

        # Melody: Peak prominence + harmonic prominence in 400-4000 Hz
        if np.any(melody_mask) and eff_melody > 0.4:
            melody_mag = mag[melody_mask]
            sorted_peaks = np.sort(melody_mag)[-4:]
            median_energy = float(np.median(melody_mag)) + 1e-6
            peak_prominence = float(np.mean(sorted_peaks)) / median_energy
            melody_candidate = min(1.0, max(0.0, (peak_prominence - 2.2) * 0.24))
        else:
            melody_candidate = 0.0
        melody_val = melody_candidate if self.melody_gate.update(melody_candidate) else 0.0

        # Beat: Rhythmic combination of transients + spectral flux
        if self.prev_spectrum is not None and len(self.prev_spectrum) == len(mag):
            flux = np.sum(np.maximum(0.0, mag - self.prev_spectrum))
            flux_val = min(1.0, max(0.0, float(flux * 0.00010)))
        else:
            flux_val = 0.0
        self.prev_spectrum = mag.copy()

        # Weighted combination of rhythmically active components
        beat_val = min(1.0, max(0.0, 0.45 * kick_val + 0.30 * snare_val + 0.15 * hihat_val + 0.10 * flux_val))

        # Overall: Blended RMS and multi-feature activity
        rms_component = min(1.0, max(0.0, effective_rms * 6.0))
        feature_mean = (kick_val + snare_val + hihat_val + sustained_bass + vocal_val + melody_val) / 6.0
        overall_val = min(1.0, max(0.0, 0.65 * rms_component + 0.35 * feature_mean))

        # =========================================================================
        # 8. SMOOTHING FOR SUSTAINED FEATURES
        # =========================================================================
        sustained_updates = {
            "bass": (sustained_bass, 0.60, 0.20),
            "vocal": (vocal_val, 0.55, 0.18),
            "brass": (brass_val, 0.50, 0.18),
            "melody": (melody_val, 0.50, 0.16),
            "beat": (beat_val, 0.65, 0.25),
            "overall": (overall_val, 0.58, 0.20)
        }

        # Musical attack/release per sustained feature
        for k, (target, attack_rate, release_rate) in sustained_updates.items():
            prev = self.smooth_features[k]
            rate = attack_rate if target > prev else release_rate
            self.smooth_features[k] = prev * (1.0 - rate) + target * rate
            if self.smooth_features[k] < 0.01:
                self.smooth_features[k] = 0.0

        # Publish diagnostics
        self._publish_diagnostics(is_gate_open=True, kick_trig=kick_trig, snare_trig=snare_trig, hihat_trig=hihat_trig)

        # Throttled debug log (once per 2 seconds)
        if now - self.last_debug_log_time > 2.0:
            self.last_debug_log_time = now
            logger.debug(
                f"[AudioV2] NoiseFloor: {self.noise_tracker.get_floor('rms'):.3f} | "
                f"Bass: {self.smooth_features['bass']:.2f} | "
                f"Kick: {'[*]' if kick_trig else '[ ]'} ({kick_val:.2f}) | "
                f"Snare: {'[*]' if snare_trig else '[ ]'} | "
                f"HiHat: {'[*]' if hihat_trig else '[ ]'} | "
                f"Melody: {self.smooth_features['melody']:.2f} | "
                f"Gate: {'OPEN' if is_music_active else 'CLOSED'}"
            )

        return MusicAnalysis(
            bass=float(self.smooth_features["bass"]),
            kick=float(kick_val),
            snare=float(snare_val),
            vocal=float(self.smooth_features["vocal"]),
            hihat=float(hihat_val),
            brass=float(self.smooth_features["brass"]),
            melody=float(self.smooth_features["melody"]),
            beat=float(self.smooth_features["beat"]),
            overall=float(self.smooth_features["overall"]),
            kick_trigger=kick_trig,
            snare_trigger=snare_trig,
            hihat_trigger=hihat_trig,
            music_gate_open=is_music_active,
            bass_transient=float(bass_transient_val)
        )

    def _publish_diagnostics(self, is_gate_open: bool, kick_trig: bool, snare_trig: bool, hihat_trig: bool):
        try:
            import diagnostics as diag
            diag.diagnostics.set_metric("audio_noise_floor", round(self.noise_tracker.get_floor("rms"), 4))
            diag.diagnostics.set_metric("audio_music_gate", is_gate_open)
            diag.diagnostics.set_metric("audio_kick_trigger", kick_trig)
            diag.diagnostics.set_metric("audio_snare_trigger", snare_trig)
            diag.diagnostics.set_metric("audio_hihat_trigger", hihat_trig)
        except Exception:
            pass

# Backward compatibility alias
SpectralFeatureExtractor = SpectralFeatureExtractorV2

class MusicAnalyzer:
    """
    Main audio capture service.
    Opens audio stream using native sample rate and publishes MusicAnalysis to engine.
    """
    def __init__(self, lighting_engine, extractor: BaseFeatureExtractor = None):
        self.engine = lighting_engine
        self.extractor = extractor or SpectralFeatureExtractorV2()
        
        self.running = False
        self.thread = None
        self.status = "stopped"
        
        self.sample_rate = 44100
        self.chunk_size = 2048
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
            # Query default input device and discover native sample rate
            dev_info = sd.query_devices(kind='input')
            if not dev_info:
                self.status = "no_device"
                logger.error("No audio input device found.")
                return

            device_name = dev_info.get('name', 'Unknown')
            self.sample_rate = int(dev_info.get('default_samplerate', 44100))
            logger.info(f"Opening audio stream on: '{device_name}' at {self.sample_rate} Hz (chunk={self.chunk_size})")

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
                            # Fallback single color
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
