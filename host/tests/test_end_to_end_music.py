import sys
import os
import time
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app_state import AppState, AppMode
from lighting_engine import LightingEngine
from transports import DynamicTransport, SerialTransport, VirtualTransport
from music_models import MusicAnalysis, MusicMapping, RGBColor, LED_COUNT

class TestEndToEndMusic(unittest.TestCase):
    def setUp(self):
        self.test_config = "test_e2e_config.json"
        if os.path.exists(self.test_config):
            os.remove(self.test_config)
        self.app_state = AppState(self.test_config)
        # Set smoothing to 0 for instant convergence in tests
        self.app_state.settings["custom"]["smoothing"] = 0.0

    def tearDown(self):
        if os.path.exists(self.test_config):
            os.remove(self.test_config)

    def test_mode_switching_and_protocol_emission(self):
        virtual_transport = VirtualTransport()
        virtual_transport.connect()
        mock_serial = MagicMock()
        mock_serial.is_open = True

        transport = DynamicTransport(self.app_state)
        transport.serial_transport.ser = mock_serial
        transport.serial_transport.is_connected = lambda: True

        engine = LightingEngine(transport, self.app_state)
        engine.smoothing_factor = 0.0

        try:
            # 1. Start in Custom Mode (Protocol V1)
            self.app_state.set_mode(AppMode.CUSTOM)
            engine.set_ambient_color(255, 50, 20)
            engine.set_user_brightness(1.0)
            
            time.sleep(0.15)

            # In custom mode, frame should be uniform color and V1 packet sent
            self.assertEqual(len(engine.led_frame), 300)
            self.assertEqual(engine.render_state.r, 255)
            self.assertEqual(engine.render_state.g, 50)
            self.assertEqual(engine.render_state.b, 20)

            # 2. Switch to Music Mode (Protocol V2)
            self.app_state.set_mode(AppMode.MUSIC)
            self.app_state.set_music_response_mode("fade")
            self.app_state.apply_music_preset("default_3_band")

            # Feed music analysis
            analysis = MusicAnalysis(bass=1.0, vocal=0.5, hihat=0.8)
            engine.process_music_analysis(analysis)
            time.sleep(0.15)

            # Verify multi-zone frame
            frame = engine.led_frame
            self.assertEqual(len(frame), 300)

            # LEDs 1-100 (Bass: Red)
            self.assertEqual(frame[0], (255, 0, 0))
            self.assertEqual(frame[99], (255, 0, 0))

            # LEDs 101-200 (Vocal: Green at 0.5 intensity)
            self.assertEqual(frame[100], (0, int(255 * 0.5), 0))
            self.assertEqual(frame[199], (0, int(255 * 0.5), 0))

            # LEDs 201-300 (HiHat: Blue at 0.8 intensity)
            self.assertEqual(frame[200], (0, 0, int(255 * 0.8)))
            self.assertEqual(frame[299], (0, 0, int(255 * 0.8)))

            # 3. Test Global Brightness Slider (0.5)
            engine.set_user_brightness(0.5)
            time.sleep(0.15)
            half_frame = engine.led_frame
            # Bass should now be 255 * 0.5 = 127
            self.assertEqual(half_frame[0], (127, 0, 0))

            # 4. Test Power OFF (all black)
            self.app_state.set_power(False)
            time.sleep(0.15)
            off_frame = engine.led_frame
            for led in off_frame:
                self.assertEqual(led, (0, 0, 0))

            # 5. Test Power ON restores zones
            self.app_state.set_power(True)
            time.sleep(0.15)
            on_frame = engine.led_frame
            self.assertEqual(on_frame[0], (127, 0, 0))

        finally:
            engine.stop()

    def test_persistence_and_preset_population(self):
        # Apply Party preset and verify mappings
        self.app_state.apply_music_preset("party")
        mappings = self.app_state.get_music_mappings()
        self.assertEqual(len(mappings), 6)
        
        instruments = [m["instrument"] for m in mappings]
        self.assertEqual(instruments, ["bass", "kick", "snare", "vocal", "hihat", "melody"])

        # Reload AppState from the same config file to simulate restart
        reloaded = AppState(self.test_config)
        reloaded_mappings = reloaded.get_music_mappings()
        self.assertEqual(len(reloaded_mappings), 6)
        self.assertEqual(reloaded_mappings[0]["instrument"], "bass")
        self.assertEqual(reloaded_mappings[1]["instrument"], "kick")

if __name__ == '__main__':
    unittest.main()
