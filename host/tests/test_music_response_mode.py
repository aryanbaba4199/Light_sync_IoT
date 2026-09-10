import sys
import os
import time
import unittest
import tempfile
import json
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from music_models import MusicAnalysis, MusicMapping, RGBColor, MusicResponseMode
from music_mapping_engine import MusicMappingEngine, FlashEventManager
from app_state import AppState

class TestMusicResponseMode(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.json")
        self.app_state = AppState(config_file=self.config_path)
        self.engine = MusicMappingEngine(led_count=300)

    def tearDown(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_default_response_mode_is_flash(self):
        """AppState defaults to 'flash' mode when unconfigured."""
        mode = self.app_state.get_music_response_mode()
        self.assertEqual(mode, "flash")

    def test_response_mode_persistence(self):
        """Response mode persists across saves and reloads."""
        self.assertTrue(self.app_state.set_music_response_mode("fade"))
        self.assertEqual(self.app_state.get_music_response_mode(), "fade")

        # Reload from disk
        reloaded = AppState(config_file=self.config_path)
        self.assertEqual(reloaded.get_music_response_mode(), "fade")

        # Change back to flash
        self.assertTrue(reloaded.set_music_response_mode("flash"))
        self.assertEqual(reloaded.get_music_response_mode(), "flash")

        # Invalid mode should be rejected
        self.assertFalse(reloaded.set_music_response_mode("rainbow"))
        self.assertEqual(reloaded.get_music_response_mode(), "flash")

    def test_flash_mode_strictly_binary_output(self):
        """In FLASH mode, LED output is strictly 0% (OFF) or 100% (FULL BRIGHTNESS). Never intermediate."""
        mapping = MusicMapping(
            id="kick_map",
            instrument="kick",
            color=RGBColor(255, 100, 0),
            start_led=1,
            end_led=10,
            sensitivity=1.0,
            response="static"
        )
        
        # When inactive: strictly 0 (OFF)
        analysis_inactive = MusicAnalysis(
            music_gate_open=True,
            kick=0.0,
            kick_trigger=False
        )
        frame_off = self.engine.render_frame(
            analysis_inactive, [mapping], user_brightness=1.0, mode_limit=1.0, response_mode="flash"
        )
        for i in range(10):
            self.assertEqual(frame_off[i], (0, 0, 0))

        # When transient triggered: strictly 100% (FULL COLOR: 255, 100, 0)
        # Even with fractional kick intensity (e.g. 0.45)
        analysis_active = MusicAnalysis(
            music_gate_open=True,
            kick=0.45,
            kick_trigger=True
        )
        frame_on = self.engine.render_frame(
            analysis_active, [mapping], user_brightness=1.0, mode_limit=1.0, response_mode="flash"
        )
        for i in range(10):
            self.assertEqual(frame_on[i], (255, 100, 0))

    def test_fade_mode_continuous_intermediate_output(self):
        """In FADE mode, LED output smoothly follows continuous feature intensity."""
        mapping = MusicMapping(
            id="vocal_map",
            instrument="vocal",
            color=RGBColor(200, 100, 50),
            start_led=1,
            end_led=10,
            sensitivity=1.0,
            response="static"
        )
        
        analysis = MusicAnalysis(
            music_gate_open=True,
            vocal=0.5
        )
        frame = self.engine.render_frame(
            analysis, [mapping], user_brightness=1.0, mode_limit=1.0, response_mode="fade"
        )
        # Intensity = 0.5, so color should be 200*0.5=100, 100*0.5=50, 50*0.5=25
        for i in range(10):
            self.assertEqual(frame[i], (100, 50, 25))

    def test_flash_mode_scaled_by_global_brightness(self):
        """In FLASH mode, 100% full brightness is scaled by master brightness and mode limits."""
        mapping = MusicMapping(
            id="snare_map",
            instrument="snare",
            color=RGBColor(200, 100, 50),
            start_led=1,
            end_led=10,
            sensitivity=1.0
        )
        
        analysis = MusicAnalysis(
            music_gate_open=True,
            snare=0.8,
            snare_trigger=True
        )
        
        # User brightness 50% (0.5), mode limit 80% (0.8) -> master_mult = 0.4
        frame = self.engine.render_frame(
            analysis, [mapping], user_brightness=0.5, mode_limit=0.8, response_mode="flash"
        )
        # Expected: 200 * 0.4 = 80, 100 * 0.4 = 40, 50 * 0.4 = 20
        for i in range(10):
            self.assertEqual(frame[i], (80, 40, 20))

    def test_flash_silence_and_noise_rejection(self):
        """When noise gate is closed, FLASH mode stays dark even if small audio fluctuations occur."""
        mapping = MusicMapping(
            id="bass_map",
            instrument="bass",
            color=RGBColor(255, 0, 0),
            start_led=1,
            end_led=20
        )
        
        # Room/fan noise: gate is closed, but small raw bass energy exists
        analysis_noise = MusicAnalysis(
            music_gate_open=False,
            bass=0.15,
            bass_transient=0.0
        )
        frame = self.engine.render_frame(
            analysis_noise, [mapping], user_brightness=1.0, mode_limit=1.0, response_mode="flash"
        )
        for i in range(20):
            self.assertEqual(frame[i], (0, 0, 0))

    def test_sustained_bass_in_flash_vs_fade(self):
        """A sustained low hum triggers a flash only on the initial onset in FLASH mode, but stays lit in FADE mode."""
        mapping = MusicMapping(
            id="bass_map",
            instrument="bass",
            color=RGBColor(255, 0, 0),
            start_led=1,
            end_led=10,
            response="static"
        )
        
        flash_engine = MusicMappingEngine(led_count=100)
        fade_engine = MusicMappingEngine(led_count=100)

        # Frame 1: Onset of sustained bass
        analysis_onset = MusicAnalysis(music_gate_open=True, bass=0.8, bass_transient=1.0)
        f1_flash = flash_engine.render_frame(analysis_onset, [mapping], response_mode="flash")
        f1_fade = fade_engine.render_frame(analysis_onset, [mapping], response_mode="fade")

        # Both should be lit on initial hit
        self.assertEqual(f1_flash[0], (255, 0, 0))
        self.assertEqual(f1_fade[0], (204, 0, 0)) # 0.8 * 255 = 204

        # Simulate 120ms later (beyond flash hold time of ~85ms) with sustained bass but NO transient
        time.sleep(0.12)
        analysis_sustained = MusicAnalysis(music_gate_open=True, bass=0.8, bass_transient=0.0)
        f2_flash = flash_engine.render_frame(analysis_sustained, [mapping], response_mode="flash")
        f2_fade = fade_engine.render_frame(analysis_sustained, [mapping], response_mode="fade")

        # FLASH must be OFF (0, 0, 0), while FADE remains lit!
        self.assertEqual(f2_flash[0], (0, 0, 0))
        self.assertGreater(f2_fade[0][0], 150)

    def test_concurrent_transient_events(self):
        """Simultaneous Kick + HiHat transients flash both zones simultaneously without interference."""
        m_kick = MusicMapping(
            id="m_kick",
            instrument="kick",
            color=RGBColor(255, 0, 0),
            start_led=1,
            end_led=10
        )
        m_hihat = MusicMapping(
            id="m_hihat",
            instrument="hihat",
            color=RGBColor(0, 255, 255),
            start_led=11,
            end_led=20
        )

        analysis = MusicAnalysis(
            music_gate_open=True,
            kick=0.9,
            kick_trigger=True,
            hihat=0.8,
            hihat_trigger=True
        )

        frame = self.engine.render_frame(analysis, [m_kick, m_hihat], response_mode="flash")

        # LEDs 1-10 should be Red
        for i in range(0, 10):
            self.assertEqual(frame[i], (255, 0, 0))
        # LEDs 11-20 should be Cyan
        for i in range(10, 20):
            self.assertEqual(frame[i], (0, 255, 255))
        # Remaining LEDs off
        for i in range(20, 300):
            self.assertEqual(frame[i], (0, 0, 0))

    def test_extract_zones_for_protocol_flash_mode(self):
        """extract_zones_for_protocol returns brightness 255 or 0 in flash mode."""
        mapping = MusicMapping(
            id="snare_map",
            instrument="snare",
            color=RGBColor(255, 200, 0),
            start_led=1,
            end_led=50
        )
        
        # Active
        analysis_on = MusicAnalysis(music_gate_open=True, snare=0.6, snare_trigger=True)
        zones_on = self.engine.extract_zones_for_protocol(analysis_on, [mapping], user_brightness=1.0, response_mode="flash")
        self.assertEqual(len(zones_on), 1)
        self.assertEqual(zones_on[0]["r"], 255)

        # Inactive
        analysis_off = MusicAnalysis(music_gate_open=True, snare=0.0, snare_trigger=False)
        # Advance clock to ensure flash expired
        time.sleep(0.1)
        zones_off = self.engine.extract_zones_for_protocol(analysis_off, [mapping], user_brightness=1.0, response_mode="flash")
        self.assertEqual(len(zones_off), 1)
        self.assertEqual(zones_off[0]["r"], 0)

if __name__ == '__main__':
    unittest.main()
