import json
import os

class AppMode:
    MOVIE = "movie"
    MUSIC = "music"
    DEVELOPER = "developer"
    GAME = "game"
    CUSTOM = "custom"

class AppState:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.mode = AppMode.MOVIE
        self.output_mode = "auto" # 'auto', 'virtual', 'esp32'
        self.power_on = True
        
        # Default settings
        self.settings = {
            "movie": {"smoothing": 0.8, "brightness_limit": 1.0},
            "music": {"smoothing": 0.5, "brightness_limit": 1.0},
            "developer": {"smoothing": 0.8, "brightness_limit": 0.7},
            "game": {"smoothing": 0.2, "brightness_limit": 1.0}, 
            "custom": {"r": 255, "g": 255, "b": 255, "brightness": 1.0, "smoothing": 0.5}
        }
        self.load()
        
    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.mode = data.get("mode", self.mode)
                    self.output_mode = data.get("output_mode", self.output_mode)
                    self.power_on = data.get("power_on", self.power_on)
                    if "settings" in data:
                        for k, v in data["settings"].items():
                            if k in self.settings:
                                self.settings[k].update(v)
            except Exception as e:
                print(f"Failed to load config: {e}")

    def save(self):
        tmp_file = self.config_file + ".tmp"
        try:
            with open(tmp_file, 'w') as f:
                json.dump({
                    "mode": self.mode,
                    "output_mode": self.output_mode,
                    "power_on": self.power_on,
                    "settings": self.settings
                }, f, indent=4)
            os.replace(tmp_file, self.config_file)
        except Exception as e:
            print(f"Failed to save config: {e}")
            
    def set_mode(self, mode):
        if hasattr(AppMode, mode.upper()):
            self.mode = mode
            self.save()
            return self.get_current_settings()
        return None
        
    def set_power(self, is_on):
        self.power_on = bool(is_on)
        self.save()

    def set_output_mode(self, mode):
        if mode in ["auto", "virtual", "esp32"]:
            self.output_mode = mode
            self.save()
            
    def get_current_settings(self):
        return self.settings.get(self.mode, self.settings["movie"])
