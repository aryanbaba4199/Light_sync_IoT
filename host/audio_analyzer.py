import numpy as np
from base_audio import BaseAudioAnalyzer

class AudioAnalyzer(BaseAudioAnalyzer):
    def __init__(self, lighting_engine):
        super().__init__(lighting_engine, chunk=1024)

    def process_audio_data(self, audio_data):
        # Calculate RMS (amplitude)
        rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
        
        # Normalize intensity (0 to 1)
        intensity = min(1.0, rms / 10000.0)
        
        # Update lighting engine
        self.lighting_engine.set_ambient_brightness(intensity)

if __name__ == "__main__":
    import time
    from lighting_engine import LightingEngine
    
    class DummyComm:
        def send_command(self, r, g, b, bright):
            print(f"To HW -> Br:{bright:.2f} (Audio Intensity)")

    engine = LightingEngine(DummyComm())
    analyzer = AudioAnalyzer(engine)
    
    print("Starting audio analysis test. Press Ctrl+C to stop.")
    try:
        analyzer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        analyzer.stop()
        print("Stopped.")
