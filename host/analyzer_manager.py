import logging
from app_state import AppMode
from analyzers.screen_analyzer import ScreenAnalyzer
from analyzers.music_analyzer import MusicAnalyzer

logger = logging.getLogger(__name__)

class AnalyzerManager:
    def __init__(self, lighting_engine, app_state):
        self.engine = lighting_engine
        self.app_state = app_state
        self.screen_analyzer = ScreenAnalyzer(lighting_engine)
        self.music_analyzer = MusicAnalyzer(lighting_engine)
        
    def check_state(self):
        """
        Called when the app_state changes.
        Starts or stops analyzers based on the active mode.
        """
        mode = self.app_state.mode
        
        if mode in [AppMode.MOVIE, AppMode.GAME]:
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
                
        else: # custom or other
            if self.screen_analyzer.running:
                logger.info(f"Mode is {mode}, stopping Screen Analyzer")
                self.screen_analyzer.stop()
            if self.music_analyzer.running:
                logger.info(f"Mode is {mode}, stopping Music Analyzer")
                self.music_analyzer.stop()

    def get_status(self):
        return {
            "screen_analyzer": self.screen_analyzer.status,
            "music_analyzer": self.music_analyzer.status
        }
