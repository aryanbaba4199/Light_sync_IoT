import numpy as np
from base_audio import BaseAudioAnalyzer

class MusicAnalyzer(BaseAudioAnalyzer):
    def __init__(self, lighting_engine):
        super().__init__(lighting_engine, chunk=2048)

    def process_audio_data(self, audio_data):
        # Overall intensity
        rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
        intensity = min(1.0, rms / 10000.0)
        
        # FFT for frequency bands
        window = np.hanning(len(audio_data))
        fft_data = np.abs(np.fft.rfft(audio_data * window))
        freqs = np.fft.rfftfreq(len(audio_data), 1.0/self.rate)
        
        # Define bands
        bass_idx = np.where((freqs >= 20) & (freqs <= 150))[0]
        mid_idx = np.where((freqs > 150) & (freqs <= 2000))[0]
        high_idx = np.where((freqs > 2000) & (freqs <= 10000))[0]
        
        bass_energy = np.sum(fft_data[bass_idx]) if len(bass_idx) > 0 else 0
        mid_energy = np.sum(fft_data[mid_idx]) if len(mid_idx) > 0 else 0
        high_energy = np.sum(fft_data[high_idx]) if len(high_idx) > 0 else 0
        
        # Normalize and map to RGB
        norm_factor = 5000000.0
        r = min(255, int((bass_energy / norm_factor) * 255))
        g = min(255, int((mid_energy / norm_factor) * 255))
        b = min(255, int((high_energy / (norm_factor*0.5)) * 255))
        
        # Feed color and brightness separately
        self.lighting_engine.set_ambient_color(r, g, b)
        self.lighting_engine.set_ambient_brightness(intensity)
