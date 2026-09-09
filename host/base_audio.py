import pyaudio
import numpy as np
import time
import threading

class BaseAudioAnalyzer:
    def __init__(self, lighting_engine, chunk=1024):
        self.lighting_engine = lighting_engine
        self.running = False
        self.thread = None
        
        self.chunk = chunk
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        
        self.p = pyaudio.PyAudio()
        
        try:
            self.device_index = self.p.get_default_input_device_info()['index']
        except IOError:
            self.device_index = None
            print("No default audio input device found.")

    def start(self):
        if self.device_index is None:
            return
        self.running = True
        self.thread = threading.Thread(target=self._audio_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            # We don't join here to prevent UI freezing. The thread is daemon anyway.
            self.thread = None
            
        # Proper PyAudio cleanup
        if self.p:
            self.p.terminate()
            self.p = None

    def process_audio_data(self, audio_data):
        raise NotImplementedError("Subclasses must implement process_audio_data")

    def _audio_loop(self):
        if not self.p:
            return
            
        stream = self.p.open(format=self.format,
                             channels=self.channels,
                             rate=self.rate,
                             input=True,
                             input_device_index=self.device_index,
                             frames_per_buffer=self.chunk)
                             
        while self.running:
            start_time = time.time()
            try:
                data = stream.read(self.chunk, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                self.process_audio_data(audio_data)
                
                audio_ms = (time.time() - start_time) * 1000.0
                import diagnostics as diag
                diag.diagnostics.set_metric("audio_ms", audio_ms)
            except Exception as e:
                time.sleep(0.1)
                
        stream.stop_stream()
        stream.close()
