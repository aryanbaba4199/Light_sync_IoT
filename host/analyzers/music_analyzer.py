"""
Audio Analyzer & Feature Extraction V2 for DevLights.

Features:
- System / Desktop Audio primary capture via CoreAudio loopback drivers (BlackHole, Loopback).
- No silent fallback to microphone; explicit reporting if loopback driver is unavailable.
- Low-cut filter (< 45 Hz) to eliminate desk vibrations and mechanical AC/fan rumble.
- Adaptive Per-Band & Master Noise Floor estimation with asymmetric leaky integration.
- Master Musical Activity Gate (Schmitt trigger / hysteresis).
- Kick vs. Bass separation: Kick = low-end onset transient event; Bass = sustained musical envelope.
- Clap vs. Hi-Hat separation: Clap = broadband mid/high transient (1.2–5.5 kHz); Hi-Hat = high-end upper band (>6.5 kHz).
- Advanced Vocal detection: 300–3400 Hz formant concentration + harmonic peak prominence + Wiener spectral flatness - percussion transient suppression - sub-bass dominance penalty + Attack-Hold-Decay vocal smoothing.
- Melody harmonic prominence in 400–4000 Hz with local spectral normalization and hysteresis.
- Brass spectral centroid in horn formant range (1200–2800 Hz).
- Live telemetry metrics published to Diagnostics and WebSocket clients.
"""
import time
import threading
import logging
from typing import Tuple, Dict, Optional, Any
import numpy as np
import scipy.fftpack
import scipy.signal
import scipy.ndimage

try:
    from music_models import MusicAnalysis
except ImportError:
    from host.music_models import MusicAnalysis

try:
    from audio_sources import AudioSource, SystemAudioSource, create_audio_source
except ImportError:
    from host.audio_sources import AudioSource, SystemAudioSource, create_audio_source

logger = logging.getLogger("MusicAnalyzer")


class HysteresisGate:
    """Schmitt trigger to prevent rapid flickering around a threshold, with musical hold time."""
    def __init__(self, open_thresh: float = 0.25, close_thresh: float = 0.15, hold_sec: float = 0.0):
        self.open_thresh = open_thresh
        self.close_thresh = close_thresh
        self.hold_sec = hold_sec
        self.is_open = False
        self.hold_until = 0.0

    def update(self, value: float, now: float = None) -> bool:
        if np.isnan(value) or np.isinf(value):
            return self.is_open
        if now is None:
            now = time.time()
        if self.is_open:
            if value >= self.close_thresh:
                self.hold_until = now + self.hold_sec
            else:
                if now >= self.hold_until:
                    self.is_open = False
        else:
            if value >= self.open_thresh:
                self.is_open = True
                self.hold_until = now + self.hold_sec
        return self.is_open


class AdaptiveNoiseFloor:
    """
    Asymmetric leaky integrator for per-band and overall noise floor tracking.
    Adapts downward quickly when quiet; creeps upward smoothly to track ambient noise floors.
    """
    def __init__(self, alpha_up: float = 0.035, alpha_down: float = 0.05, margin: float = 1.15):
        self.alpha_up = alpha_up
        self.alpha_down = alpha_down
        self.margin = margin
        self.floors: Dict[str, float] = {
            "rms": 0.005,
            "bass": 0.05,
            "kick": 0.05,
            "clap": 0.05,
            "snare": 0.05,  # Backward compatibility alias
            "hihat": 0.02,
            "vocal": 0.05,
            "brass": 0.05,
            "melody": 0.05,
        }

    def update(self, key: str, value: float, custom_margin: float = None, custom_alpha_up: float = None) -> float:
        if np.isnan(value) or np.isinf(value):
            return 0.0
        m = custom_margin if custom_margin is not None else self.margin
        a_up = custom_alpha_up if custom_alpha_up is not None else self.alpha_up
        if key not in self.floors:
            self.floors[key] = max(0.001, float(value))
            return 0.0

        floor = self.floors[key]
        if np.isnan(floor) or np.isinf(floor):
            floor = 0.005 if key == "rms" else 0.05
        if value < floor:
            floor = floor * (1.0 - self.alpha_down) + value * self.alpha_down
        else:
            floor = floor * (1.0 - a_up) + value * a_up
        self.floors[key] = floor

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


class VocalEnvelope:
    """
    Attack-Hold-Decay envelope designed specifically for vocal tracking.
    Smooths micro-pauses between vocal phonemes and prevents visual flicker.
    """
    def __init__(self, hold_sec: float = 0.160, decay_sec: float = 0.280, attack_rate: float = 0.35):
        self.hold_sec = hold_sec
        self.decay_sec = decay_sec
        self.attack_rate = attack_rate
        self.current_val = 0.0
        self.hold_until = 0.0
        self.last_time = time.time()

    def update(self, target: float, now: float = None) -> float:
        if now is None:
            now = time.time()
        dt = max(0.001, min(0.1, now - self.last_time))
        self.last_time = now

        if target >= self.current_val:
            # Smooth musical attack
            self.current_val = self.current_val * (1.0 - self.attack_rate) + target * self.attack_rate
            if self.current_val >= 0.15:
                self.hold_until = now + self.hold_sec
        else:
            if now < self.hold_until:
                # Hold during short singing pauses
                return self.current_val
            # Exponential decay
            decay_factor = max(0.0, 1.0 - (dt / self.decay_sec))
            self.current_val *= decay_factor
            if self.current_val < 0.015:
                self.current_val = 0.0

        return max(0.0, min(1.0, self.current_val))

    def clear(self):
        self.current_val = 0.0
        self.hold_until = 0.0


class BaseFeatureExtractor:
    """Interface for audio feature extraction."""
    def extract(self, audio_data: np.ndarray, sample_rate: int) -> MusicAnalysis:
        raise NotImplementedError


class YINPitchTracker:
    """
    Real-Time YIN Fundamental Frequency (F0) & Pitch Confidence Estimator.
    Optimized for singing voice detection (80–450 Hz) in real-time streaming audio.
    Uses FFT-accelerated circular difference function, Cumulative Mean Normalized Difference
    Function (CMNDF), parabolic interpolation, and bandpass pre-filtering.
    Execution time: ~0.05 ms per frame.
    """
    def __init__(self, sample_rate: int = 44100, min_f0: float = 80.0, max_f0: float = 450.0, threshold: float = 0.20):
        self.sample_rate = sample_rate
        self.min_f0 = min_f0
        self.max_f0 = max_f0
        self.threshold = threshold
        self.last_pitch = 0.0
        self.last_confidence = 0.0
        self._filter_sr = None
        self._b = None
        self._a = None

    def compute_pitch(self, audio_data: np.ndarray, sample_rate: int = None) -> Tuple[float, float]:
        sr = sample_rate or self.sample_rate
        if len(audio_data) < 128:
            return 0.0, 0.0

        rms = float(np.sqrt(np.mean(np.square(audio_data))))
        if rms < 0.008:
            self.last_pitch = 0.0
            self.last_confidence = 0.0
            return 0.0, 0.0

        # Vocal range bandpass filter: eliminates deep sub-bass and high cymbal noise
        if self._filter_sr != sr or self._b is None:
            self._filter_sr = sr
            nyq = sr / 2.0
            low = max(0.01, 80.0 / nyq)
            high = min(0.95, 1200.0 / nyq)
            self._b, self._a = scipy.signal.butter(2, [low, high], btype='band')

        filtered = scipy.signal.lfilter(self._b, self._a, audio_data)

        # Decimate by 2 if sample rate is high (faster FFT, smoother F0)
        decimate_factor = 2 if sr >= 40000 else 1
        x = filtered[::decimate_factor]
        effective_sr = sr // decimate_factor

        tau_min = max(2, int(effective_sr / self.max_f0))
        tau_max = int(effective_sr / self.min_f0)

        if len(x) <= tau_max + 10:
            tau_max = max(tau_min + 5, len(x) - 10)

        w = len(x) - tau_max
        if w <= 10:
            return 0.0, 0.0

        x_analysis = x[:w + tau_max]
        x_w = x[:w]
        n = len(x_analysis)

        fft_len = 1 << (2 * n - 1).bit_length()
        X = np.fft.rfft(x_analysis, fft_len)
        X_w = np.fft.rfft(x_w, fft_len)
        conv = np.fft.irfft(X * np.conj(X_w), fft_len)[:tau_max + 1]

        cum_sq = np.concatenate(([0.0], np.cumsum(x_analysis**2)))
        tau_idx = np.arange(tau_max + 1)
        e_tau = cum_sq[w + tau_idx] - cum_sq[tau_idx]
        e_0 = cum_sq[w]
        d = np.maximum(0.0, e_0 + e_tau - 2.0 * conv)
        d[0] = 0.0

        # Cumulative Mean Normalized Difference Function
        cmndf = np.zeros(tau_max + 1)
        cmndf[0] = 1.0
        cum_d = np.cumsum(d[1:])
        divisor = cum_d / np.arange(1, tau_max + 1)
        cmndf[1:] = np.where(divisor > 1e-9, d[1:] / divisor, 1.0)

        if tau_min >= len(cmndf) or tau_max >= len(cmndf):
            return 0.0, 0.0

        valid_range = cmndf[tau_min:tau_max + 1]
        if len(valid_range) == 0:
            return 0.0, 0.0

        below = np.where(valid_range < self.threshold)[0]
        if len(below) > 0:
            cand = below[0] + tau_min
            while cand + 1 <= tau_max and cmndf[cand + 1] < cmndf[cand]:
                cand += 1
            best_tau = cand
        else:
            best_tau = int(np.argmin(valid_range)) + tau_min

        score = float(cmndf[best_tau])
        confidence = max(0.0, min(1.0, 1.0 - score))

        best_tau_interp = float(best_tau)
        if tau_min < best_tau < tau_max:
            s0 = cmndf[best_tau - 1]
            s1 = cmndf[best_tau]
            s2 = cmndf[best_tau + 1]
            denom = 2 * (2 * s1 - s0 - s2)
            if abs(denom) > 1e-9:
                delta = (s2 - s0) / denom
                best_tau_interp = best_tau + delta

        pitch = (effective_sr / best_tau_interp) if best_tau_interp > 0 else 0.0
        self.last_pitch = float(pitch)
        self.last_confidence = float(confidence)
        return float(pitch), float(confidence)


class RealtimeHPSS:
    """
    Real-Time Harmonic-Percussive Source Separation (HPSS).
    Maintains a rolling 2D spectrogram buffer and applies 2D median filtering:
    - Harmonic filter: horizontal median filter along time (axis 1)
    - Percussive filter: vertical median filter along frequency (axis 0)
    Generates soft Wiener masks to separate harmonic (sustained voice/chords/bass)
    from percussive (drum hits, claps, transients).
    Execution time: ~0.9 ms per frame.
    """
    def __init__(self, n_bins: int = 1025, n_frames: int = 7, l_harm: int = 5, l_perc: int = 15):
        self.n_bins = n_bins
        self.n_frames = n_frames
        self.l_harm = min(l_harm, n_frames)
        self.l_perc = l_perc
        self.buffer = np.zeros((n_bins, n_frames), dtype=np.float32)
        self.frame_count = 0

    def update(self, mag_frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        if len(mag_frame) != self.n_bins:
            self.n_bins = len(mag_frame)
            self.buffer = np.zeros((self.n_bins, self.n_frames), dtype=np.float32)
            self.frame_count = 0

        self.buffer[:, :-1] = self.buffer[:, 1:]
        self.buffer[:, -1] = mag_frame.astype(np.float32)
        self.frame_count += 1

        if self.frame_count < 2:
            return mag_frame, mag_frame, 0.5

        # 1. Harmonic filter: median along time (axis 1)
        h_med = scipy.ndimage.median_filter(self.buffer, size=(1, self.l_harm), mode='reflect')

        # 2. Percussive filter: median along frequency (axis 0)
        p_med = scipy.ndimage.median_filter(self.buffer, size=(self.l_perc, 1), mode='constant', cval=0.0)

        h_last = h_med[:, -1]
        p_last = p_med[:, -1]

        h_sq = h_last ** 2
        p_sq = p_last ** 2
        denom = h_sq + p_sq + 1e-9

        low_energy = (h_sq + p_sq) < 1e-6
        mask_h = np.where(low_energy, 0.5, h_sq / denom)
        mask_p = np.where(low_energy, 0.5, p_sq / denom)

        mag_h = mag_frame * mask_h
        mag_p = mag_frame * mask_p

        total_energy = float(np.sum(mag_frame)) + 1e-9
        harmonic_ratio = float(np.sum(mag_h) / total_energy)
        harmonic_ratio = max(0.0, min(1.0, harmonic_ratio))

        return mag_h, mag_p, harmonic_ratio

    def clear(self):
        self.buffer.fill(0.0)
        self.frame_count = 0


class SpectralFeatureExtractorV2(BaseFeatureExtractor):
    """
    Advanced Music Feature Extraction Engine:
    - Low-cut rumble filter (< 45 Hz)
    - Master Musical Activity Gate (Schmitt trigger hysteresis)
    - Adaptive per-band noise floor subtraction
    - Kick: low-band spectral flux + onset ratio + refractory cooldown (event-based)
    - Bass: sustained low-frequency envelope follower (level-based)
    - Clap: broadband mid/high transient (1.2–5.5 kHz) with sharp onset
    - Hi-Hat: upper-band transient (>6.5 kHz) with high-to-mid ratio check
    - Vocal: 300–3400 Hz formant presence + harmonic peak prominence + Wiener flatness
             - percussion transient suppression - sub-bass dominance penalty
             + VocalEnvelope (attack/hold/decay)
    - Melody: harmonic prominence in 400–4000 Hz
    - Brass: spectral centroid focus in 1200–2800 Hz
    - Beat: composite rhythm
    - Overall: multi-feature + RMS energy
    """
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

        # Noise Floor Trackers
        self.noise_tracker = AdaptiveNoiseFloor(alpha_up=0.035, alpha_down=0.05, margin=1.20)

        # Master Activity Gate (Hysteresis with musical hold time)
        self.music_gate = HysteresisGate(open_thresh=0.015, close_thresh=0.008, hold_sec=0.050)

        # Transient Onset Detectors (Event signals)
        self.kick_detector = TransientDetector(min_energy=0.65, min_rise=0.40, refractory_sec=0.085)
        self.clap_detector = TransientDetector(min_energy=0.75, min_rise=0.45, refractory_sec=0.080)
        self.hihat_detector = TransientDetector(min_energy=0.25, min_rise=0.18, refractory_sec=0.060)
        self.bass_transient_detector = TransientDetector(min_energy=0.65, min_rise=0.40, refractory_sec=0.085)

        # Attack-Hold-Decay Envelopes for Transients
        self.kick_env = TransientEnvelope(hold_sec=0.035, decay_sec=0.120)
        self.clap_env = TransientEnvelope(hold_sec=0.030, decay_sec=0.130)
        self.hihat_env = TransientEnvelope(hold_sec=0.015, decay_sec=0.075)
        self.bass_transient_env = TransientEnvelope(hold_sec=0.035, decay_sec=0.120)

        # Vocal Dedicated Envelope & Gating (responsive to human singing formants)
        self.vocal_gate = HysteresisGate(open_thresh=0.10, close_thresh=0.05)
        self.vocal_env = VocalEnvelope(hold_sec=0.180, decay_sec=0.250, attack_rate=0.40)

        # Melody Gate
        self.melody_gate = HysteresisGate(open_thresh=0.22, close_thresh=0.12)

        # Smooth memory for sustained features
        self.smooth_features = {
            "bass": 0.0,
            "vocal": 0.0,
            "brass": 0.0,
            "melody": 0.0,
            "beat": 0.0,
            "overall": 0.0
        }

        # Spectral memory for flux calculation
        self.prev_spectrum = None
        self.prev_kick_mag = None
        self.prev_clap_mag = None
        self.last_debug_log_time = 0.0

        # Advanced MIR Engines: Real-Time HPSS & YIN Pitch Tracker
        self.hpss = RealtimeHPSS(n_bins=1025, n_frames=7, l_harm=5, l_perc=15)
        self.yin = YINPitchTracker(sample_rate=self.sample_rate)

        # Time tracking for simulated test frames and real-time audio sync
        self._last_process_time = None
        self._simulated_time = 0.0
        self.running_rms = 0.08

    def extract(self, audio_data: np.ndarray, sample_rate: int) -> MusicAnalysis:
        frame_dt = len(audio_data) / float(sample_rate) if sample_rate > 0 else 0.046
        now_wall = time.time()
        if self._last_process_time is None:
            now = now_wall
        else:
            elapsed = now_wall - self._last_process_time
            now = self._simulated_time + max(elapsed, frame_dt)
        self._last_process_time = now_wall
        self._simulated_time = now
        self.sample_rate = sample_rate

        # Defensively sanitize input signal against NaNs, infs, denormals
        audio_data = np.nan_to_num(audio_data, nan=0.0, posinf=1.0, neginf=-1.0)
        audio_data = np.clip(audio_data, -1.0, 1.0)

        # 1. High-Pass Filter (< 45 Hz) to eliminate desk vibrations and mechanical rumble
        if not hasattr(self, '_hp_filter_sr') or self._hp_filter_sr != sample_rate:
            self._hp_filter_sr = sample_rate
            self._hp_b, self._hp_a = scipy.signal.butter(4, 45.0 / (sample_rate / 2.0), btype='high')
        filtered_audio = scipy.signal.lfilter(self._hp_b, self._hp_a, audio_data)
        filtered_audio = np.nan_to_num(filtered_audio, nan=0.0, posinf=1.0, neginf=-1.0)

        # 2. RMS Energy on filtered signal
        rms = float(np.sqrt(np.mean(np.square(filtered_audio))))
        effective_rms = self.noise_tracker.update("rms", rms, custom_margin=1.25)
        is_music_active = self.music_gate.update(effective_rms, now=now)

        # 3. FFT Computation with Hanning Window
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

        # 5. Real-Time HPSS & YIN Vocal Pitch Tracking
        mag_h, mag_p, harmonic_ratio = self.hpss.update(mag)
        pitch_hz, pitch_conf = self.yin.compute_pitch(audio_data, sample_rate)

        # Dynamic gain / AGC for quiet listening levels
        if is_music_active:
            self.running_rms = self.running_rms * 0.97 + rms * 0.03
        gain = float(np.clip(0.12 / max(0.015, self.running_rms), 1.0, 5.0))

        # 6. Extract Raw Band Energies & Update Adaptive Noise Floors
        # Bass: 45–150 Hz (harmonic stream + total floor)
        bass_mask = (f >= 45) & (f <= 150)
        raw_bass_h = float(np.mean(mag_h[bass_mask])) if np.any(bass_mask) else 0.0
        raw_bass_tot = float(np.mean(mag[bass_mask])) if np.any(bass_mask) else 0.0
        raw_bass = max(raw_bass_h, 0.50 * raw_bass_tot) * gain
        eff_bass = self.noise_tracker.update("bass", raw_bass, custom_margin=1.25, custom_alpha_up=0.008)

        # Kick: 45–110 Hz (percussive transient stream + total floor)
        kick_mask = (f >= 45) & (f <= 110)
        raw_kick_p = float(np.mean(mag_p[kick_mask])) if np.any(kick_mask) else 0.0
        raw_kick_tot = float(np.mean(mag[kick_mask])) if np.any(kick_mask) else 0.0
        raw_kick = max(raw_kick_p, 0.70 * raw_kick_tot) * gain
        eff_kick = self.noise_tracker.update("kick", raw_kick, custom_margin=1.20, custom_alpha_up=0.012)

        # Clap: 350–5500 Hz (percussive transient stream + total floor)
        clap_mask = (f >= 350) & (f <= 5500)
        if np.any(clap_mask):
            clap_p = mag_p[clap_mask]
            top_clap_p = np.sort(clap_p)[-int(max(4, len(clap_p) * 0.25)):]
            raw_clap_p = float(np.mean(top_clap_p))
            clap_tot = mag[clap_mask]
            top_clap_tot = np.sort(clap_tot)[-int(max(4, len(clap_tot) * 0.25)):]
            raw_clap_tot = float(np.mean(top_clap_tot))
            raw_clap = max(raw_clap_p, 0.60 * raw_clap_tot) * gain
        else:
            raw_clap = 0.0
        eff_clap = self.noise_tracker.update("clap", raw_clap, custom_margin=1.15, custom_alpha_up=0.010)
        # Update snare noise floor key for compatibility
        self.noise_tracker.update("snare", raw_clap, custom_margin=1.15, custom_alpha_up=0.010)

        # Hi-Hat: 6500–16000 Hz (percussive stream + total floor)
        hihat_mask = (f >= 6500) & (f <= 16000)
        if np.any(hihat_mask):
            hh_p = mag_p[hihat_mask]
            top_hh_p = np.sort(hh_p)[-int(max(4, len(hh_p) * 0.15)):]
            raw_hihat_p = float(np.mean(top_hh_p))
            hh_tot = mag[hihat_mask]
            top_hh_tot = np.sort(hh_tot)[-int(max(4, len(hh_tot) * 0.15)):]
            raw_hihat_tot = float(np.mean(top_hh_tot))
            raw_hihat = max(raw_hihat_p, 0.60 * raw_hihat_tot) * gain
        else:
            raw_hihat = 0.0
        eff_hihat = self.noise_tracker.update("hihat", raw_hihat, custom_margin=1.15, custom_alpha_up=0.010)

        # Vocal: 300–3400 Hz (Formants F1, F2, F3 from harmonic stream)
        vocal_mask = (f >= 300) & (f <= 3400)
        if np.any(vocal_mask):
            top_vocal_peaks = np.sort(mag_h[vocal_mask])[-6:]
            raw_vocal_h = float(np.mean(top_vocal_peaks))
            raw_vocal_tot = float(np.mean(np.sort(mag[vocal_mask])[-6:]))
            raw_vocal = max(raw_vocal_h, 0.45 * raw_vocal_tot) * gain
        else:
            raw_vocal = 0.0
        eff_vocal = self.noise_tracker.update("vocal", raw_vocal, custom_margin=1.10, custom_alpha_up=0.005)

        # Brass: 600–3200 Hz (harmonic stream)
        brass_mask = (f >= 600) & (f <= 3200)
        raw_brass = float(np.mean(mag_h[brass_mask])) * gain if np.any(brass_mask) else 0.0
        eff_brass = self.noise_tracker.update("brass", raw_brass, custom_margin=1.18, custom_alpha_up=0.010)

        # Melody: 400–4000 Hz (harmonic stream)
        melody_mask = (f >= 400) & (f <= 4000)
        if np.any(melody_mask):
            top_melody_peaks = np.sort(mag_h[melody_mask])[-6:]
            raw_melody_h = float(np.mean(top_melody_peaks))
            raw_melody_tot = float(np.mean(np.sort(mag[melody_mask])[-6:]))
            raw_melody = max(raw_melody_h, 0.45 * raw_melody_tot) * gain
        else:
            raw_melody = 0.0
        eff_melody = self.noise_tracker.update("melody", raw_melody, custom_margin=1.12, custom_alpha_up=0.006)

        # Band Spectral Flux
        if self.prev_kick_mag is not None and len(self.prev_kick_mag) == np.sum(kick_mask):
            flux_kick = float(np.sum(np.maximum(0.0, mag[kick_mask] - self.prev_kick_mag)))
        else:
            flux_kick = 0.0
        self.prev_kick_mag = mag[kick_mask].copy() if np.any(kick_mask) else None

        if self.prev_clap_mag is not None and len(self.prev_clap_mag) == np.sum(clap_mask):
            flux_clap = float(np.sum(np.maximum(0.0, mag[clap_mask] - self.prev_clap_mag)))
        else:
            flux_clap = 0.0
        self.prev_clap_mag = mag[clap_mask].copy() if np.any(clap_mask) else None

        # 7. Master Gate Closed -> Rapid Decay & Blackout
        if not is_music_active:
            for k in self.smooth_features:
                self.smooth_features[k] *= 0.50
                if self.smooth_features[k] < 0.05:
                    self.smooth_features[k] = 0.0

            # Clear transient and vocal envelopes, reset HPSS
            self.hpss.clear()
            self.kick_env.clear()
            self.clap_env.clear()
            self.hihat_env.clear()
            self.bass_transient_env.clear()
            self.vocal_env.clear()

            self._publish_diagnostics(
                is_gate_open=False, kick_trig=False, clap_trig=False, hihat_trig=False,
                pitch=0.0, pitch_conf=0.0, harmonic_ratio=0.0
            )
            return MusicAnalysis(
                bass=float(self.smooth_features["bass"]),
                kick=float(self.kick_env.current_val),
                clap=float(self.clap_env.current_val),
                vocal=float(self.smooth_features["vocal"]),
                hihat=float(self.hihat_env.current_val),
                brass=float(self.smooth_features["brass"]),
                melody=float(self.smooth_features["melody"]),
                beat=float(self.smooth_features["beat"]),
                overall=float(self.smooth_features["overall"]),
                kick_trigger=False,
                clap_trigger=False,
                hihat_trigger=False,
                music_gate_open=False,
                bass_transient=float(self.bass_transient_env.current_val),
                vocal_pitch=0.0,
                vocal_confidence=0.0,
                harmonic_ratio=0.0
            )

        # =========================================================================
        # 7. INSTRUMENT DETECTION (MUSIC ACTIVE)
        # =========================================================================

        # --- BASS (Sustained Envelope) ---
        # Continuous level tracking; does NOT require a transient; smooth attack & decay
        sustained_bass = min(1.0, max(0.0, (eff_bass - 0.35) * 0.22))
        bass_trig, bass_trig_int = self.bass_transient_detector.process(eff_bass, now)
        if bass_trig:
            self.bass_transient_env.trigger(bass_trig_int, now)
        bass_transient_val = self.bass_transient_env.update(now)

        # --- KICK (Transient Event) ---
        # Low-frequency transient with onset flux & refractory cooldown
        kick_trig, kick_int = self.kick_detector.process(eff_kick, now)
        # Low-frequency dominance check: suppress kick if clap/mid energy vastly dominates
        if kick_trig and (eff_clap > eff_kick * 2.0):
            kick_trig = False
            kick_int = 0.0
        # Sustained tone check: a continuous tone has zero flux after onset; suppress false re-triggers
        if kick_trig and (flux_kick < 0.12 * max(0.01, eff_kick)):
            kick_trig = False
            kick_int = 0.0
        if kick_trig:
            self.kick_env.trigger(kick_int, now)
        kick_val = self.kick_env.update(now)

        # --- CLAP vs. HI-HAT ---
        clap_trig, clap_int = self.clap_detector.process(eff_clap, now)
        hihat_trig, hihat_int = self.hihat_detector.process(eff_hihat, now)

        # Discrimination:
        # Hi-hat has concentrated high energy (>6.5 kHz) with high ratio over mid
        hi_ratio = raw_hihat / (raw_clap + 1e-6)
        if hi_ratio > 0.90 and hihat_trig:
            # Upper frequency dominates -> Favor Hi-Hat, suppress Clap
            clap_trig = False
            clap_int = 0.0
        elif hi_ratio <= 0.65 and raw_clap > 0.40 and clap_trig:
            # Broadband mid dominates -> Favor Clap, suppress Hi-Hat
            hihat_trig = False
            hihat_int = 0.0

        if clap_trig:
            self.clap_env.trigger(clap_int, now)
        clap_val = self.clap_env.update(now)

        if hihat_trig:
            self.hihat_env.trigger(hihat_int, now)
        hihat_val = self.hihat_env.update(now)

        # --- VOCAL (Harmonic Formants + YIN Pitch Tracking + Temporal Syllabic Envelope) ---
        if np.any(vocal_mask) and eff_vocal > 0.05:
            vocal_mag = np.maximum(mag_h[vocal_mask], 0.40 * mag[vocal_mask])
            med_vocal = float(np.median(vocal_mag)) + 1e-6
            top_peaks = np.sort(vocal_mag)[-4:]
            harmonic_prominence = float(np.mean(top_peaks)) / med_vocal

            # Wiener spectral flatness (Geometric Mean / Arithmetic Mean)
            log_mean = float(np.mean(np.log(vocal_mag + 1e-9)))
            geom_mean = float(np.exp(log_mean))
            arith_mean = float(np.mean(vocal_mag)) + 1e-9
            flatness = min(1.0, max(0.0, geom_mean / arith_mean))

            # Voiced harmonics & formant prominence:
            # Singing voice exhibits strong discrete harmonics and low spectral flatness
            harmonic_score = min(1.0, max(0.0, (harmonic_prominence - 2.0) / 4.0))
            tonal_score = min(1.0, max(0.0, (0.55 - flatness) / 0.35))
            spectral_confidence = 0.55 * harmonic_score + 0.35 * tonal_score + 0.10

            # Fusion with YIN pitch tracker:
            # When YIN detects glottal singing pitch (80–450 Hz) with confidence:
            yin_active = (pitch_conf >= 0.40) and (80.0 <= pitch_hz <= 450.0)
            if yin_active:
                vocal_confidence = min(1.0, 0.60 * pitch_conf + 0.40 * spectral_confidence + 0.10)
            else:
                vocal_confidence = spectral_confidence

            # Suppress if unvoiced / pure broadband noise (e.g. cymbal crash or white noise)
            if vocal_confidence < 0.28:
                raw_candidate = 0.0
            else:
                # Normalized vocal energy above adaptive floor
                vocal_floor = self.noise_tracker.get_floor("vocal")
                norm_vocal = min(1.0, max(0.0, eff_vocal / (vocal_floor * 1.5 + 0.1)))
                raw_candidate = min(1.0, max(0.0, norm_vocal * vocal_confidence * 1.35))
        else:
            vocal_confidence = 0.0
            raw_candidate = 0.0

        # Gated by Schmitt trigger
        vocal_gated = raw_candidate if self.vocal_gate.update(raw_candidate, now=now) else 0.0
        # Smoothed with Attack-Hold-Decay Vocal Envelope
        vocal_val = self.vocal_env.update(vocal_gated, now)

        # --- BRASS ---
        # Spectral centroid focus in horn formant range (1200–2800 Hz)
        if np.any(brass_mask) and eff_brass > 0.20:
            brass_mag = mag[brass_mask]
            brass_f = f[brass_mask]
            total_m = np.sum(brass_mag)
            centroid = np.sum(brass_f * brass_mag) / (total_m + 1e-6)
            c_factor = 1.0 if (1200 <= centroid <= 2800) else 0.45
            brass_val = min(1.0, max(0.0, eff_brass * 0.080 * c_factor))
        else:
            brass_val = 0.0

        # --- MELODY ---
        # Peak prominence in lead melody range (400–4000 Hz)
        if np.any(melody_mask) and eff_melody > 0.35:
            melody_mag = mag[melody_mask]
            sorted_peaks = np.sort(melody_mag)[-4:]
            med_m = float(np.median(melody_mag)) + 1e-6
            peak_prom = float(np.mean(sorted_peaks)) / med_m
            melody_candidate = min(1.0, max(0.0, (peak_prom - 2.2) * 0.24))
        else:
            melody_candidate = 0.0
        melody_val = melody_candidate if self.melody_gate.update(melody_candidate, now=now) else 0.0

        # --- BEAT & OVERALL ---
        if self.prev_spectrum is not None and len(self.prev_spectrum) == len(mag):
            flux = np.sum(np.maximum(0.0, mag - self.prev_spectrum))
            flux_val = min(1.0, max(0.0, float(flux * 0.00010)))
        else:
            flux_val = 0.0
        self.prev_spectrum = mag.copy()

        beat_val = min(1.0, max(0.0, 0.40 * kick_val + 0.30 * clap_val + 0.15 * hihat_val + 0.15 * flux_val))
        rms_comp = min(1.0, max(0.0, effective_rms * 6.0))
        feature_mean = (kick_val + clap_val + hihat_val + sustained_bass + vocal_val + melody_val) / 6.0
        overall_val = min(1.0, max(0.0, 0.65 * rms_comp + 0.35 * feature_mean))

        # =========================================================================
        # 8. SMOOTHING FOR SUSTAINED FEATURES
        # =========================================================================
        sustained_updates = {
            "bass": (sustained_bass, 0.50, 0.15),
            "vocal": (vocal_val, 0.45, 0.15),
            "brass": (brass_val, 0.45, 0.18),
            "melody": (melody_val, 0.45, 0.16),
            "beat": (beat_val, 0.65, 0.25),
            "overall": (overall_val, 0.55, 0.20)
        }

        for k, (target, attack_rate, release_rate) in sustained_updates.items():
            if np.isnan(target) or np.isinf(target):
                continue
            if k == "vocal":
                # VocalEnvelope already encapsulates dedicated Attack-Hold-Decay envelope
                self.smooth_features[k] = 0.0 if (np.isnan(vocal_val) or np.isinf(vocal_val)) else vocal_val
                continue
            prev = self.smooth_features[k]
            if np.isnan(prev) or np.isinf(prev):
                prev = 0.0
            rate = attack_rate if target > prev else release_rate
            self.smooth_features[k] = prev * (1.0 - rate) + target * rate
            if self.smooth_features[k] < 0.01 or np.isnan(self.smooth_features[k]):
                self.smooth_features[k] = 0.0

        # Publish diagnostics
        self._publish_diagnostics(
            is_gate_open=True, kick_trig=kick_trig, clap_trig=clap_trig, hihat_trig=hihat_trig,
            pitch=pitch_hz, pitch_conf=pitch_conf, harmonic_ratio=harmonic_ratio
        )

        # Throttled debug log (once per 2 seconds)
        if now - self.last_debug_log_time > 2.0:
            self.last_debug_log_time = now
            logger.debug(
                f"[AudioV3] Floor: {self.noise_tracker.get_floor('rms'):.3f} | "
                f"Bass: {self.smooth_features['bass']:.2f} | "
                f"Kick: {'[*]' if kick_trig else '[ ]'} ({kick_val:.2f}) | "
                f"Clap: {'[*]' if clap_trig else '[ ]'} ({clap_val:.2f}) | "
                f"HiHat: {'[*]' if hihat_trig else '[ ]'} ({hihat_val:.2f}) | "
                f"Vocal: {self.smooth_features['vocal']:.2f} (Pitch: {pitch_hz:.1f}Hz, Conf: {pitch_conf:.2f}) | "
                f"HarmRatio: {harmonic_ratio:.2f} | "
                f"Gate: {'OPEN' if is_music_active else 'CLOSED'}"
            )

        return MusicAnalysis(
            bass=float(self.smooth_features["bass"]),
            kick=float(kick_val),
            clap=float(clap_val),
            vocal=float(self.smooth_features["vocal"]),
            hihat=float(hihat_val),
            brass=float(self.smooth_features["brass"]),
            melody=float(self.smooth_features["melody"]),
            beat=float(self.smooth_features["beat"]),
            overall=float(self.smooth_features["overall"]),
            kick_trigger=kick_trig,
            clap_trigger=clap_trig,
            hihat_trigger=hihat_trig,
            music_gate_open=is_music_active,
            bass_transient=float(bass_transient_val),
            vocal_pitch=float(pitch_hz),
            vocal_confidence=float(pitch_conf),
            harmonic_ratio=float(harmonic_ratio)
        )

    def _publish_diagnostics(
        self,
        is_gate_open: bool,
        kick_trig: bool,
        clap_trig: bool,
        hihat_trig: bool,
        pitch: float = 0.0,
        pitch_conf: float = 0.0,
        harmonic_ratio: float = 0.0
    ):
        try:
            import diagnostics as diag
            diag.diagnostics.set_metric("audio_noise_floor", round(self.noise_tracker.get_floor("rms"), 4))
            diag.diagnostics.set_metric("audio_music_gate", is_gate_open)
            diag.diagnostics.set_metric("audio_kick_trigger", kick_trig)
            diag.diagnostics.set_metric("audio_clap_trigger", clap_trig)
            diag.diagnostics.set_metric("audio_snare_trigger", clap_trig)
            diag.diagnostics.set_metric("audio_hihat_trigger", hihat_trig)
            diag.diagnostics.set_metric("audio_vocal_pitch", round(pitch, 1))
            diag.diagnostics.set_metric("audio_vocal_confidence", round(pitch_conf, 3))
            diag.diagnostics.set_metric("audio_harmonic_ratio", round(harmonic_ratio, 3))
        except Exception:
            pass


# Backward compatibility alias
SpectralFeatureExtractor = SpectralFeatureExtractorV2


class MusicAnalyzer:
    """
    Main audio capture & feature extraction service.
    Consumes an AudioSource (defaulting to SystemAudioSource for system/desktop audio).
    Does NOT silently fall back to the microphone.
    """
    def __init__(
        self,
        lighting_engine,
        extractor: Optional[BaseFeatureExtractor] = None,
        source_type: str = "system",
        preferred_device: Optional[str] = None,
        audio_source: Optional[AudioSource] = None
    ):
        self.engine = lighting_engine
        self.extractor = extractor or SpectralFeatureExtractorV2()
        self.source_type = source_type
        self.preferred_device = preferred_device
        self.audio_source = audio_source or create_audio_source(
            source_type=self.source_type,
            preferred_device=self.preferred_device,
            chunk_size=2048
        )

        self.running = False
        self.thread = None
        self.status = self.audio_source.status
        self.sample_rate = self.audio_source.sample_rate
        self.chunk_size = self.audio_source.chunk_size
        self.latest_analysis = MusicAnalysis()

    def set_audio_source(self, source_type: str, preferred_device: Optional[str] = None):
        """Allows switching audio source (e.g. system vs explicit debug microphone)."""
        was_running = self.running
        if was_running:
            self.stop()

        self.source_type = source_type
        self.preferred_device = preferred_device
        self.audio_source = create_audio_source(
            source_type=source_type,
            preferred_device=preferred_device,
            chunk_size=self.chunk_size
        )
        self.status = self.audio_source.status
        self.sample_rate = self.audio_source.sample_rate

        if was_running:
            self.start()

    def start(self):
        if self.running:
            return
        self.running = True
        self.status = "starting"
        self.thread = threading.Thread(target=self._analyze_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.audio_source:
            self.audio_source.stop()
        self.status = "stopped"
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            self.thread = None

    def _analyze_loop(self):
        try:
            started = self.audio_source.start()
            if not started:
                self.status = self.audio_source.status
                logger.warning(
                    f"Audio source '{self.audio_source.name}' did not start ({self.status}): "
                    f"{self.audio_source.status_message}"
                )

            self.status = self.audio_source.status
            self.sample_rate = self.audio_source.sample_rate
            self.chunk_size = self.audio_source.chunk_size

            last_diagnostic_log = 0.0

            # Rolling analysis window: retains 2048-sample FFT frequency resolution while
            # processing low-latency chunks (512 or 1024 samples) with sub-60ms response time
            window_size = max(2048, self.chunk_size)
            analysis_window = np.zeros(window_size, dtype=np.float32)

            while self.running:
                samples, is_valid = self.audio_source.read()
                now = time.time()

                if not is_valid:
                    self.status = self.audio_source.status
                    if now - last_diagnostic_log > 5.0:
                        last_diagnostic_log = now
                        logger.info(f"MusicAnalyzer audio status: {self.status} - {self.audio_source.status_message}")

                # Update rolling analysis window
                chunk_len = len(samples)
                if chunk_len < window_size:
                    analysis_window = np.roll(analysis_window, -chunk_len)
                    analysis_window[-chunk_len:] = samples
                    window_to_extract = analysis_window
                else:
                    window_to_extract = samples

                # Extract audio features on high-resolution window
                analysis = self.extractor.extract(window_to_extract, self.sample_rate)
                analysis.audio_source = self.audio_source.name
                analysis.audio_device = self.audio_source.device_name
                analysis.audio_status = self.audio_source.status
                self.latest_analysis = analysis

                # Pass analysis to the lighting engine
                if self.engine:
                    if hasattr(self.engine, "process_music_analysis"):
                        self.engine.process_music_analysis(analysis)
                    else:
                        r = int(analysis.bass * 255)
                        g = int(analysis.vocal * 255)
                        b = int(analysis.hihat * 255)
                        self.engine.set_ambient_color(r, g, b)
                        self.engine.set_ambient_brightness(analysis.overall)

                if not is_valid:
                    # Sleep briefly when device is unavailable/streaming zeros to prevent CPU spin
                    time.sleep(0.04)

        except Exception as e:
            self.status = f"error: {str(e)}"
            logger.error(f"Error in MusicAnalyzer: {e}")
            self.running = False
        finally:
            if self.audio_source:
                self.audio_source.stop()
