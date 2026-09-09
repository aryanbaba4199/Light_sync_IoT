import logging
from app_state import AppMode
from analyzers.screen_analyzer import ScreenAnalyzer

logger = logging.getLogger(__name__)

class AnalyzerManager:
    def __init__(self, lighting_engine, app_state):
        self.engine = lighting_engine
        self.app_state = app_state
        self.screen_analyzer = ScreenAnalyzer(lighting_engine)
        
    def check_state(self):
        """
        Called when the app_state changes (e.g. user selects a new mode).
        Starts or stops analyzers based on the active mode.
        """
        mode = self.app_state.mode
        
        # Modes that require screen capture
        if mode in [AppMode.MOVIE, AppMode.GAME]:
            if not self.screen_analyzer.running:
                logger.info(f"Mode is {mode}, starting Screen Analyzer")
                self.screen_analyzer.start()
        else:
            if self.screen_analyzer.running:
                logger.info(f"Mode is {mode}, stopping Screen Analyzer")
                self.screen_analyzer.stop()

    def get_status(self):
        """Returns the status payload for the UI."""
        return {
            "screen_analyzer": self.screen_analyzer.status
        }
