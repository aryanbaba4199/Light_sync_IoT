import unittest
import numpy as np
from audio_sources import (
    AudioSource,
    SystemAudioSource,
    MicrophoneAudioSource,
    SyntheticAudioSource,
    create_audio_source
)

class TestAudioSources(unittest.TestCase):
    def test_default_source_is_system(self):
        """create_audio_source() defaults strictly to SystemAudioSource."""
        source = create_audio_source()
        self.assertIsInstance(source, SystemAudioSource)
        self.assertEqual(source.name, "system")

    def test_microphone_is_not_silently_selected_when_loopback_missing(self):
        """When no loopback audio device exists, SystemAudioSource reports unavailable without falling back to mic."""
        source = SystemAudioSource()
        # On machines without a virtual loopback device (like BlackHole), status must be system_audio_unavailable
        if source.device_index is None:
            self.assertEqual(source.status, "system_audio_unavailable")
            self.assertIn("BlackHole", source.status_message)
            self.assertNotEqual(source.device_name, "Default Microphone")
            # Calling read returns zeros safely
            samples, ok = source.read()
            self.assertEqual(len(samples), source.chunk_size)
            self.assertFalse(ok)
            self.assertTrue(np.all(samples == 0.0))

    def test_microphone_source_explicit_selection_only(self):
        """MicrophoneAudioSource is only created when explicitly requested."""
        mic = create_audio_source(source_type="microphone")
        self.assertIsInstance(mic, MicrophoneAudioSource)
        self.assertEqual(mic.name, "microphone")

    def test_synthetic_audio_source_lifecycle(self):
        """SyntheticAudioSource starts, queues buffers, pads, and returns them deterministically."""
        synth = SyntheticAudioSource(chunk_size=1024)
        self.assertEqual(synth.status, "ready")
        self.assertTrue(synth.start())
        self.assertTrue(synth.running)

        # Queue test buffer
        test_buf = np.ones(512, dtype=np.float32) * 0.75
        synth.queue_buffer(test_buf)

        read_buf, ok = synth.read()
        self.assertTrue(ok)
        self.assertEqual(len(read_buf), 1024)
        self.assertAlmostEqual(read_buf[0], 0.75)
        # Verify padding
        self.assertEqual(read_buf[600], 0.0)

    def test_list_audio_input_devices(self):
        """list_audio_input_devices returns a list of dictionaries with classification."""
        from audio_sources import list_audio_input_devices
        devices = list_audio_input_devices()
        self.assertIsInstance(devices, list)
        for dev in devices:
            self.assertIn("id", dev)
            self.assertIn("name", dev)
            self.assertIn("type", dev)
            self.assertIn(dev["type"], ["system", "microphone"])

    def test_app_state_audio_source_selection(self):
        """AppState correctly persists and toggles audio_source and system_audio_device."""
        from app_state import AppState
        import os
        config_path = "test_audio_src_config.json"
        try:
            state = AppState(config_file=config_path)
            # Default is system
            self.assertEqual(state.get_music_audio_source(), "system")
            
            # Switch to microphone
            self.assertTrue(state.set_music_audio_source("microphone", "USB Mic"))
            self.assertEqual(state.get_music_audio_source(), "microphone")
            self.assertEqual(state.get_music_audio_device(), "USB Mic")

            # Switch back to system
            self.assertTrue(state.set_music_audio_source("system"))
            self.assertEqual(state.get_music_audio_source(), "system")

            # Reject invalid source
            self.assertFalse(state.set_music_audio_source("invalid_source"))
        finally:
            if os.path.exists(config_path):
                os.remove(config_path)


if __name__ == '__main__':
    unittest.main()
