"""
Audio Source abstraction for DevLights Music Mode.

Enforces:
1. System/Desktop Audio as the default source of truth.
2. Detection of virtual audio loopback drivers (BlackHole, Loopback, Background Music, etc.).
3. No silent fallback to microphone when system audio is unavailable.
4. Detailed setup/diagnostic messages when a loopback device is missing.
5. Microphone available strictly as an explicit debug option.
6. Synthetic audio source for unit tests and simulation.
"""

import abc
import re
import time
import logging
from typing import Optional, Dict, Any, Tuple, List
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

logger = logging.getLogger("AudioSources")

# Known virtual loopback audio drivers on macOS, Windows, Linux
SYSTEM_LOOPBACK_PATTERNS = [
    r"blackhole",
    r"loopback",
    r"soundflower",
    r"background\s*music",
    r"swb\s*audio",
    r"virtual\s*(audio|cable)",
    r"cable\s*(input|output|audio)",
    r"stereo\s*mix",
    r"what\s*u\s*hear",
    r"monitor\s*of",
    r"aggregate",
    r"multi-output",
]


def list_audio_input_devices() -> List[Dict[str, Any]]:
    """
    Returns all detected audio input devices with classification
    ('system' for virtual loopback, 'microphone' for physical inputs).
    """
    devices = []
    if sd is None:
        return devices

    try:
        raw_devices = sd.query_devices()
        default_in = None
        try:
            default_in = sd.default.device[0]
        except Exception:
            pass

        for idx, dev in enumerate(raw_devices):
            max_in = dev.get("max_input_channels", 0)
            if max_in > 0:
                name = dev.get("name", f"Device {idx}")
                is_loopback = any(
                    re.search(pat, name, re.IGNORECASE) for pat in SYSTEM_LOOPBACK_PATTERNS
                )
                devices.append({
                    "id": idx,
                    "name": name,
                    "channels": max_in,
                    "sample_rate": int(dev.get("default_samplerate", 44100)),
                    "type": "system" if is_loopback else "microphone",
                    "is_default": (idx == default_in)
                })
    except Exception as e:
        logger.warning(f"Error querying audio input devices: {e}")

    return devices


class AudioSource(abc.ABC):
    """Abstract base class for all audio sources."""

    def __init__(self, name: str, chunk_size: int = 2048):
        self.name = name
        self.chunk_size = chunk_size
        self.sample_rate: int = 44100
        self.channels: int = 1
        self.status: str = "stopped"
        self.status_message: str = ""
        self.device_name: str = "None"
        self.device_index: Optional[int] = None
        self.running: bool = False

    @abc.abstractmethod
    def start(self) -> bool:
        """Starts the audio source stream. Returns True if started successfully."""
        pass

    @abc.abstractmethod
    def stop(self):
        """Stops the audio source stream."""
        pass

    @abc.abstractmethod
    def read(self) -> Tuple[np.ndarray, bool]:
        """
        Reads one chunk of float32 audio samples in [-1.0, 1.0].
        Returns (samples_array, is_valid).
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        return {
            "source_type": self.name,
            "device_name": self.device_name,
            "device_index": self.device_index,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "status": self.status,
            "status_message": self.status_message,
            "running": self.running,
        }


class SystemAudioSource(AudioSource):
    """
    Default source for Music Mode.
    Captures system / desktop audio via CoreAudio virtual loopback drivers.
    If no loopback driver is present, it explicitly reports 'system_audio_unavailable'
    and does NOT silently fall back to the microphone.
    """

    def __init__(self, preferred_device: Optional[str] = None, chunk_size: int = 2048):
        super().__init__(name="system", chunk_size=chunk_size)
        self.preferred_device = preferred_device
        self._stream = None
        self._find_device()

    def _find_device(self):
        if sd is None:
            self.status = "error"
            self.status_message = "sounddevice library is not available"
            return

        try:
            devices = sd.query_devices()
        except Exception as e:
            self.status = "error"
            self.status_message = f"Failed to query audio devices: {str(e)}"
            return

        # 1. If preferred_device is specified, search for exact or substring match
        if self.preferred_device:
            pref_lower = self.preferred_device.lower()
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    name = dev.get("name", "")
                    if pref_lower in name.lower():
                        self.device_index = idx
                        self.device_name = name
                        self.sample_rate = int(dev.get("default_samplerate", 44100))
                        self.channels = 1
                        self.status = "ready"
                        self.status_message = f"Configured system loopback device: {name}"
                        logger.info(f"SystemAudioSource matched preferred device: '{name}' (id={idx})")
                        return

        # 2. Search for known system audio loopback patterns
        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0:
                name = dev.get("name", "")
                name_lower = name.lower()
                for pattern in SYSTEM_LOOPBACK_PATTERNS:
                    if re.search(pattern, name_lower):
                        self.device_index = idx
                        self.device_name = name
                        self.sample_rate = int(dev.get("default_samplerate", 44100))
                        self.channels = 1
                        self.status = "ready"
                        self.status_message = f"Detected virtual loopback device: {name}"
                        logger.info(f"SystemAudioSource detected loopback device: '{name}' (id={idx})")
                        return

        # 3. No loopback device found: DO NOT silently use the microphone!
        self.device_index = None
        self.device_name = "None (No Loopback Device)"
        self.status = "system_audio_unavailable"
        self.status_message = (
            "System audio loopback driver not found. macOS requires a virtual loopback device "
            "(e.g. BlackHole 2ch: 'brew install --cask blackhole-2ch' or Loopback) configured as "
            "a Multi-Output Device in Audio MIDI Setup. Microphone fallback is NOT silently selected."
        )
        logger.warning("SystemAudioSource: System audio unavailable. " + self.status_message)

    def start(self) -> bool:
        if self.running:
            return True

        if self.device_index is None:
            # Re-scan in case the user plugged in / created the device recently
            self._find_device()

        if self.device_index is None:
            self.running = False
            self.status = "system_audio_unavailable"
            return False

        try:
            # Capture up to 2 channels if available, for stereo downmixing
            channels_to_open = min(2, max(1, getattr(self, "channels", 1)))
            self._stream = sd.InputStream(
                device=self.device_index,
                samplerate=self.sample_rate,
                channels=channels_to_open,
                blocksize=self.chunk_size,
                latency="low",
                dtype="float32",
            )
            self._stream.start()
            self.running = True
            self.status = "running"
            self.status_message = f"Streaming from '{self.device_name}' at {self.sample_rate} Hz"
            logger.info(f"SystemAudioSource started on '{self.device_name}'")
            return True
        except sd.PortAudioError as e:
            msg = str(e).lower()
            if "-9986" in str(e) or "internal portaudio error" in msg:
                # CoreAudio daemon was restarted; reinitialize PortAudio subsystem
                logger.info("Detected CoreAudio reset (-9986). Re-initializing PortAudio...")
                try:
                    sd._terminate()
                    sd._initialize()
                    self._find_device()
                    if self.device_index is not None:
                        self._stream = sd.InputStream(
                            device=self.device_index,
                            samplerate=self.sample_rate,
                            channels=channels_to_open,
                            blocksize=self.chunk_size,
                            latency="low",
                            dtype="float32",
                        )
                        self._stream.start()
                        self.running = True
                        self.status = "running"
                        self.status_message = f"Streaming from '{self.device_name}' at {self.sample_rate} Hz"
                        logger.info(f"SystemAudioSource recovered and started on '{self.device_name}'")
                        return True
                except Exception as retry_err:
                    e = retry_err

            if "permission" in msg or "not authorized" in msg:
                self.status = "permission_denied"
                self.status_message = "Microphone/audio capture permission denied by macOS."
            else:
                self.status = "error"
                self.status_message = f"PortAudio error: {str(e)}"
            self.running = False
            logger.error(f"SystemAudioSource failed to start: {self.status_message}")
            return False
        except Exception as e:
            self.status = "error"
            self.status_message = f"Unexpected error: {str(e)}"
            self.running = False
            logger.error(f"SystemAudioSource error: {self.status_message}")
            return False

    def stop(self):
        self.running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self.status = "stopped"
        self.status_message = "Audio stream stopped"

    def read(self) -> Tuple[np.ndarray, bool]:
        if not self.running or self._stream is None:
            # Return silent zeros so downstream analyzers remain stable
            return np.zeros(self.chunk_size, dtype=np.float32), False

        try:
            data, overflowed = self._stream.read(self.chunk_size)
            if data.ndim > 1 and data.shape[1] > 1:
                samples = np.mean(data, axis=1)
            elif data.ndim > 1:
                samples = data[:, 0]
            else:
                samples = data
            # Guard against CoreAudio buffer slips, NaNs, and infinities
            samples = np.nan_to_num(samples, nan=0.0, posinf=1.0, neginf=-1.0)
            samples = np.clip(samples, -1.0, 1.0)
            return samples.astype(np.float32), True
        except Exception as e:
            logger.warning(f"SystemAudioSource read error: {e}")
            self.status = "error"
            self.status_message = f"Read interrupted: {str(e)}"
            return np.zeros(self.chunk_size, dtype=np.float32), False


class MicrophoneAudioSource(AudioSource):
    """
    Explicit debug/development-only microphone source.
    Never selected by default. Must be explicitly requested in settings.
    """

    def __init__(self, device_name_or_index: Optional[Any] = None, chunk_size: int = 2048):
        super().__init__(name="microphone", chunk_size=chunk_size)
        self.requested_device = device_name_or_index
        self._stream = None
        self._find_device()

    def _find_device(self):
        if sd is None:
            self.status = "error"
            self.status_message = "sounddevice library not available"
            return

        try:
            if self.requested_device is not None:
                if isinstance(self.requested_device, int):
                    dev = sd.query_devices(self.requested_device)
                    self.device_index = self.requested_device
                    self.device_name = dev.get("name", f"Device {self.requested_device}")
                    self.sample_rate = int(dev.get("default_samplerate", 44100))
                else:
                    pref = str(self.requested_device).lower()
                    for idx, dev in enumerate(sd.query_devices()):
                        if dev.get("max_input_channels", 0) > 0 and pref in dev.get("name", "").lower():
                            self.device_index = idx
                            self.device_name = dev.get("name", "Microphone")
                            self.sample_rate = int(dev.get("default_samplerate", 44100))
                            break
            else:
                # Default system microphone
                dev_info = sd.query_devices(kind="input")
                if dev_info:
                    self.device_name = dev_info.get("name", "Default Microphone")
                    # Find its device index
                    for idx, dev in enumerate(sd.query_devices()):
                        if dev.get("name") == self.device_name and dev.get("max_input_channels", 0) > 0:
                            self.device_index = idx
                            break
                    self.sample_rate = int(dev_info.get("default_samplerate", 44100))

            if self.device_index is not None:
                self.status = "ready"
                self.status_message = f"Microphone ready: {self.device_name}"
            else:
                self.status = "no_device"
                self.status_message = "No microphone input device found"
        except Exception as e:
            self.status = "error"
            self.status_message = f"Microphone query error: {str(e)}"

    def start(self) -> bool:
        if self.running:
            return True

        if self.device_index is None:
            self._find_device()

        if self.device_index is None:
            self.running = False
            return False

        try:
            self._stream = sd.InputStream(
                device=self.device_index,
                samplerate=self.sample_rate,
                channels=1,
                blocksize=self.chunk_size,
                latency="low",
                dtype="float32",
            )
            self._stream.start()
            self.running = True
            self.status = "running"
            self.status_message = f"Streaming from microphone: {self.device_name}"
            logger.info(f"MicrophoneAudioSource started on '{self.device_name}'")
        except Exception as e:
            if "-9986" in str(e) or "internal portaudio error" in str(e).lower():
                logger.info("Detected CoreAudio reset (-9986) in microphone source. Re-initializing...")
                try:
                    sd._terminate()
                    sd._initialize()
                    self._find_device()
                    if self.device_index is not None:
                        self._stream = sd.InputStream(
                            device=self.device_index,
                            samplerate=self.sample_rate,
                            channels=1,
                            blocksize=self.chunk_size,
                            latency="low",
                            dtype="float32",
                        )
                        self._stream.start()
                        self.running = True
                        self.status = "running"
                        self.status_message = f"Streaming from microphone: {self.device_name}"
                        logger.info(f"MicrophoneAudioSource recovered and started on '{self.device_name}'")
                        return True
                except Exception as retry_err:
                    e = retry_err

            self.status = "error"
            self.status_message = f"Failed to open microphone: {str(e)}"
            self.running = False
            return False

    def stop(self):
        self.running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self.status = "stopped"
        self.status_message = "Microphone stream stopped"

    def read(self) -> Tuple[np.ndarray, bool]:
        if not self.running or self._stream is None:
            return np.zeros(self.chunk_size, dtype=np.float32), False

        try:
            data, _ = self._stream.read(self.chunk_size)
            if data.ndim > 1 and data.shape[1] > 1:
                samples = np.mean(data, axis=1)
            elif data.ndim > 1:
                samples = data[:, 0]
            else:
                samples = data
            samples = np.nan_to_num(samples, nan=0.0, posinf=1.0, neginf=-1.0)
            samples = np.clip(samples, -1.0, 1.0)
            return samples.astype(np.float32), True
        except Exception as e:
            return np.zeros(self.chunk_size, dtype=np.float32), False


class SyntheticAudioSource(AudioSource):
    """
    In-memory synthetic audio generator for automated testing and deterministic validation.
    Supports injecting sine tones, kicks, claps, hi-hats, vocal formants, or custom buffers.
    """

    def __init__(self, sample_rate: int = 44100, chunk_size: int = 2048):
        super().__init__(name="synthetic", chunk_size=chunk_size)
        self.sample_rate = sample_rate
        self.device_name = "Synthetic Test Generator"
        self.status = "ready"
        self._queue = []

    def queue_buffer(self, samples: np.ndarray):
        """Appends audio samples to be yielded by read()."""
        self._queue.append(samples.astype(np.float32))

    def start(self) -> bool:
        self.running = True
        self.status = "running"
        self.status_message = "Synthetic generator active"
        return True

    def stop(self):
        self.running = False
        self.status = "stopped"
        self.status_message = "Synthetic generator stopped"

    def read(self) -> Tuple[np.ndarray, bool]:
        if not self.running:
            return np.zeros(self.chunk_size, dtype=np.float32), False

        if self._queue:
            buf = self._queue.pop(0)
            if len(buf) < self.chunk_size:
                padded = np.zeros(self.chunk_size, dtype=np.float32)
                padded[:len(buf)] = buf
                return padded, True
            return buf[:self.chunk_size], True

        time.sleep(0.01)
        return np.zeros(self.chunk_size, dtype=np.float32), True


def create_audio_source(
    source_type: str = "system",
    preferred_device: Optional[str] = None,
    chunk_size: int = 2048
) -> AudioSource:
    """
    Factory function for audio sources.
    Defaults strictly to 'system'.
    """
    st = str(source_type).lower().strip()
    if st == "microphone":
        return MicrophoneAudioSource(device_name_or_index=preferred_device, chunk_size=chunk_size)
    elif st == "synthetic":
        return SyntheticAudioSource(chunk_size=chunk_size)
    else:
        # Default to SystemAudioSource
        return SystemAudioSource(preferred_device=preferred_device, chunk_size=chunk_size)
