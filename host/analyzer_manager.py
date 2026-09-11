import logging
import time
from app_state import AppMode
from analyzers.screen_analyzer import ScreenAnalyzer
from analyzers.music_analyzer import MusicAnalyzer

logger = logging.getLogger(__name__)

class AnalyzerManager:
    def __init__(self, lighting_engine, app_state):
        self.engine = lighting_engine
        self.app_state = app_state
        self.screen_analyzer = ScreenAnalyzer(lighting_engine)
        audio_src = app_state.get_music_audio_source() if hasattr(app_state, "get_music_audio_source") else "system"
        audio_dev = app_state.get_music_audio_device() if hasattr(app_state, "get_music_audio_device") else None
        self.music_analyzer = MusicAnalyzer(lighting_engine, source_type=audio_src, preferred_device=audio_dev)
        
    def check_state(self):
        """
        Called when the app_state changes.
        Starts or stops analyzers based on the active mode and settings.
        """
        mode = self.app_state.mode
        
        if mode == AppMode.MOVIE:
            sync_music = False
            if hasattr(self.app_state, "settings") and "movie" in self.app_state.settings:
                sync_music = bool(self.app_state.settings["movie"].get("sync_music", False))

            if not self.screen_analyzer.running:
                logger.info("Mode is movie, starting Screen Analyzer")
                self.screen_analyzer.start()

            if sync_music:
                if not self.music_analyzer.running:
                    logger.info("Movie Mode with Sync Music enabled: starting Music Analyzer")
                    self.music_analyzer.start()
            else:
                if self.music_analyzer.running:
                    logger.info("Movie Mode with Sync Music disabled: stopping Music Analyzer")
                    self.music_analyzer.stop()

        elif mode == AppMode.GAME:
            if self.music_analyzer.running:
                logger.info(f"Mode is {mode}, stopping Music Analyzer")
                self.music_analyzer.stop()
            if not self.screen_analyzer.running:
                logger.info(f"Mode is {mode}, starting Screen Analyzer")
                self.screen_analyzer.start()
                
        elif mode == AppMode.MUSIC:
            if self.screen_analyzer.running:
                logger.info(f"Mode is {mode}, stopping Screen Analyzer")
                self.screen_analyzer.stop()
            if not self.music_analyzer.running:
                logger.info(f"Mode is {mode}, starting Music Analyzer")
                self.music_analyzer.start()
                
        else: # custom, developer, or other
            if self.screen_analyzer.running:
                logger.info(f"Mode is {mode}, stopping Screen Analyzer")
                self.screen_analyzer.stop()
            if self.music_analyzer.running:
                logger.info(f"Mode is {mode}, stopping Music Analyzer")
                self.music_analyzer.stop()

        # Check if audio source configuration changed
        audio_src = self.app_state.get_music_audio_source() if hasattr(self.app_state, "get_music_audio_source") else "system"
        audio_dev = self.app_state.get_music_audio_device() if hasattr(self.app_state, "get_music_audio_device") else None
        if hasattr(self.music_analyzer, "source_type") and (self.music_analyzer.source_type != audio_src or self.music_analyzer.preferred_device != audio_dev):
            logger.info(f"Switching audio source from {self.music_analyzer.source_type} to {audio_src}")
            self.music_analyzer.set_audio_source(audio_src, audio_dev)

    def get_available_devices(self):
        now = time.time()
        if not hasattr(self, "_cached_devices") or (now - getattr(self, "_last_devices_refresh", 0.0) > 2.5):
            try:
                from audio_sources import list_audio_input_devices
                self._cached_devices = list_audio_input_devices()
            except Exception:
                self._cached_devices = []
            self._last_devices_refresh = now
        return self._cached_devices

    def get_status(self):
        source_name = getattr(self.music_analyzer, "source_type", "system")
        device_name = "None"
        status_msg = ""
        audio_status = "ready"
        if hasattr(self.music_analyzer, "audio_source") and self.music_analyzer.audio_source:
            device_name = self.music_analyzer.audio_source.device_name
            status_msg = self.music_analyzer.audio_source.status_message
            audio_status = self.music_analyzer.audio_source.status

        return {
            "screen_analyzer": self.screen_analyzer.status,
            "music_analyzer": self.music_analyzer.status,
            "audio_source": source_name,
            "audio_device": device_name,
            "audio_status": audio_status,
            "audio_status_message": status_msg,
            "available_devices": self.get_available_devices()
        }
