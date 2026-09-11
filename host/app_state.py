import json
import os
from typing import Tuple, Optional, List

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
        
        from music_models import LED_COUNT, DEFAULT_3_BAND_PRESET, PRESETS, MusicMapping, validate_mapping
        try:
            from movie_models import MovieLayout
        except ImportError:
            from host.movie_models import MovieLayout
        try:
            from custom_effects import DEFAULT_EFFECT_CONFIGS
        except ImportError:
            from host.custom_effects import DEFAULT_EFFECT_CONFIGS
        try:
            from developer_models import DeveloperLayout
        except ImportError:
            from host.developer_models import DeveloperLayout
        self.led_count = LED_COUNT

        # Default settings
        self.settings = {
            "movie": {
                "top": 100,
                "right": 50,
                "bottom": 100,
                "left": 50,
                "sampling_thickness": 0.10,
                "clockwise": True,
                "sync_music": False,
                "smoothing": 0.70,
                "brightness_limit": 1.0,
                "min_music_brightness": 0.35,
                "max_music_brightness": 1.00
            },
            "music": {
                "smoothing": 0.5, 
                "brightness_limit": 1.0,
                "response_mode": "flash",
                "audio_source": "system",
                "system_audio_device": None,
                "mappings": [dict(m) for m in DEFAULT_3_BAND_PRESET],
                "bass_color": {"r": 255, "g": 0, "b": 0},
                "mid_color": {"r": 0, "g": 255, "b": 0},
                "treb_color": {"r": 0, "g": 0, "b": 255}
            },
            "developer": {
                "smoothing": 0.8,
                "brightness_limit": 0.7,
                "zones": DeveloperLayout.default(LED_COUNT).to_dict()
            },
            "game": {"smoothing": 0.2, "brightness_limit": 1.0}, 
            "custom": {
                "effect": "rainfall",
                "configs": {k: dict(v) for k, v in DEFAULT_EFFECT_CONFIGS.items()},
                "config": dict(DEFAULT_EFFECT_CONFIGS["rainfall"]),
                "r": 0,
                "g": 120,
                "b": 255,
                "brightness": 1.0,
                "smoothing": 0.5
            }
        }
        self.load()
        self._ensure_music_mappings()
        self._ensure_movie_settings()
        self._ensure_custom_settings()
        self._ensure_developer_settings()

    def _ensure_movie_settings(self):
        movie_conf = self.settings.setdefault("movie", {})
        dirty = False
        defaults = {
            "top": 100,
            "right": 50,
            "bottom": 100,
            "left": 50,
            "sampling_thickness": 0.10,
            "clockwise": True,
            "monitor_index": 1,
            "sync_music": False,
            "smoothing": 0.70,
            "brightness_limit": 1.0,
            "min_music_brightness": 0.35,
            "max_music_brightness": 1.00
        }
        for k, v in defaults.items():
            if k not in movie_conf:
                movie_conf[k] = v
                dirty = True
        if dirty:
            self.save()

    def _ensure_custom_settings(self):
        try:
            from custom_effects import DEFAULT_EFFECT_CONFIGS
        except ImportError:
            from host.custom_effects import DEFAULT_EFFECT_CONFIGS

        custom_conf = self.settings.setdefault("custom", {})
        dirty = False
        if "effect" not in custom_conf or custom_conf["effect"] not in DEFAULT_EFFECT_CONFIGS:
            custom_conf["effect"] = "rainfall"
            dirty = True

        configs = custom_conf.setdefault("configs", {})
        for effect_name, default_cfg in DEFAULT_EFFECT_CONFIGS.items():
            if effect_name not in configs or not isinstance(configs[effect_name], dict):
                configs[effect_name] = dict(default_cfg)
                dirty = True
            else:
                for k, v in default_cfg.items():
                    if k not in configs[effect_name]:
                        configs[effect_name][k] = v
                        dirty = True

        current_eff = custom_conf["effect"]
        custom_conf["config"] = dict(configs.get(current_eff, DEFAULT_EFFECT_CONFIGS.get(current_eff, {})))

        if "brightness" not in custom_conf:
            custom_conf["brightness"] = 1.0
            dirty = True
        if "smoothing" not in custom_conf:
            custom_conf["smoothing"] = 0.5
            dirty = True

        if dirty:
            self.save()

    def _ensure_developer_settings(self):
        try:
            from developer_models import DeveloperLayout
        except ImportError:
            from host.developer_models import DeveloperLayout

        dev_conf = self.settings.setdefault("developer", {})
        dirty = False
        if "smoothing" not in dev_conf:
            dev_conf["smoothing"] = 0.8
            dirty = True
        if "brightness_limit" not in dev_conf:
            dev_conf["brightness_limit"] = 0.7
            dirty = True

        default_layout = DeveloperLayout.default(self.led_count)
        if "zones" not in dev_conf or not isinstance(dev_conf["zones"], dict) or not dev_conf["zones"]:
            dev_conf["zones"] = default_layout.to_dict()
            dirty = True
        else:
            default_dict = default_layout.to_dict()
            for z_name, z_val in default_dict.items():
                if z_name not in dev_conf["zones"]:
                    dev_conf["zones"][z_name] = z_val
                    dirty = True

        if dirty:
            self.save()
        
    def _ensure_music_mappings(self):
        from music_models import DEFAULT_3_BAND_PRESET
        music_conf = self.settings.setdefault("music", {})
        dirty = False
        if "response_mode" not in music_conf or music_conf["response_mode"] not in ["fade", "flash"]:
            if "responseMode" in music_conf and music_conf["responseMode"] in ["fade", "flash"]:
                music_conf["response_mode"] = music_conf["responseMode"]
            else:
                music_conf["response_mode"] = "flash"
            dirty = True

        if "audio_source" not in music_conf or music_conf["audio_source"] not in ["system", "microphone"]:
            music_conf["audio_source"] = "system"
            dirty = True

        if "mappings" not in music_conf or not isinstance(music_conf["mappings"], list) or len(music_conf["mappings"]) == 0:
            music_conf["mappings"] = [dict(m) for m in DEFAULT_3_BAND_PRESET]
            # If legacy colors were set, migrate them to the 3 band preset
            if "bass_color" in music_conf:
                music_conf["mappings"][0]["color"] = music_conf["bass_color"]
            if "mid_color" in music_conf:
                music_conf["mappings"][1]["color"] = music_conf["mid_color"]
            if "treb_color" in music_conf:
                music_conf["mappings"][2]["color"] = music_conf["treb_color"]
            dirty = True
        else:
            # Normalize any legacy 'snare' mapping to 'clap'
            for m in music_conf["mappings"]:
                if m.get("instrument") == "snare":
                    m["instrument"] = "clap"
                    dirty = True

        if dirty:
            self.save()

    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.mode = data.get("mode", self.mode)
                    self.output_mode = data.get("output_mode", self.output_mode)
                    self.power_on = data.get("power_on", self.power_on)
                    self.led_count = data.get("led_count", self.led_count)
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
                    "led_count": self.led_count,
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

    def update_music_colors(self, bass, mid, treb):
        """Backward compatibility for legacy 3-band color picker."""
        if "music" in self.settings:
            if bass: self.settings["music"]["bass_color"] = bass
            if mid: self.settings["music"]["mid_color"] = mid
            if treb: self.settings["music"]["treb_color"] = treb
            # Also update the corresponding mappings if present
            mappings = self.settings["music"].get("mappings", [])
            for m in mappings:
                if m.get("instrument") == "bass" and bass:
                    m["color"] = bass
                elif m.get("instrument") == "vocal" and mid:
                    m["color"] = mid
                elif m.get("instrument") == "hihat" and treb:
                    m["color"] = treb
            self.save()

    def get_music_mappings(self) -> list:
        return self.settings.get("music", {}).get("mappings", [])

    def set_music_mappings(self, raw_mappings: list) -> Tuple[bool, Optional[str]]:
        from music_models import MusicMapping, validate_mapping
        validated = []
        for item in raw_mappings:
            try:
                mapping = MusicMapping.from_dict(item)
                is_valid, err = validate_mapping(mapping, self.led_count)
                if not is_valid:
                    return False, f"Invalid mapping '{mapping.instrument}': {err}"
                validated.append(mapping.to_dict())
            except Exception as e:
                return False, f"Malformed mapping payload: {str(e)}"

        self.settings.setdefault("music", {})["mappings"] = validated
        self.save()
        return True, None

    def set_music_mapping(self, mapping_dict: dict) -> Tuple[bool, Optional[str]]:
        from music_models import MusicMapping, validate_mapping
        try:
            mapping = MusicMapping.from_dict(mapping_dict)
            is_valid, err = validate_mapping(mapping, self.led_count)
            if not is_valid:
                return False, err
            
            mappings = self.get_music_mappings()
            found = False
            for i, m in enumerate(mappings):
                if m.get("id") == mapping.id:
                    mappings[i] = mapping.to_dict()
                    found = True
                    break
            if not found:
                mappings.append(mapping.to_dict())
                
            self.settings["music"]["mappings"] = mappings
            self.save()
            return True, None
        except Exception as e:
            return False, str(e)

    def delete_music_mapping(self, mapping_id: str) -> bool:
        mappings = self.get_music_mappings()
        new_mappings = [m for m in mappings if m.get("id") != mapping_id]
        if len(new_mappings) != len(mappings):
            self.settings["music"]["mappings"] = new_mappings
            self.save()
            return True
        return False

    def apply_music_preset(self, preset_name: str) -> bool:
        from music_models import PRESETS
        if preset_name in PRESETS:
            preset_mappings = [dict(m) for m in PRESETS[preset_name]]
            self.settings.setdefault("music", {})["mappings"] = preset_mappings
            self.save()
            return True
        return False

    def get_music_response_mode(self) -> str:
        return self.settings.get("music", {}).get("response_mode", "flash")

    def set_music_response_mode(self, mode: str) -> bool:
        if mode in ["fade", "flash"]:
            self.settings.setdefault("music", {})["response_mode"] = mode
            self.save()
            return True
        return False

    def get_music_audio_source(self) -> str:
        return self.settings.get("music", {}).get("audio_source", "system")

    def get_music_audio_device(self) -> Optional[str]:
        return self.settings.get("music", {}).get("system_audio_device", None)

    def set_music_audio_source(self, source_type: str, preferred_device: Optional[str] = None) -> bool:
        st = str(source_type).lower().strip()
        if st in ["system", "microphone"]:
            self.settings.setdefault("music", {})["audio_source"] = st
            if preferred_device is not None:
                self.settings["music"]["system_audio_device"] = preferred_device if preferred_device else None
            self.save()
            return True
        return False

    def set_output_mode(self, mode):
        if mode in ["auto", "virtual", "esp32"]:
            self.output_mode = mode
            self.save()
            
    def get_current_settings(self):
        return self.settings.get(self.mode, self.settings["movie"])

    def get_movie_layout(self):
        try:
            from movie_models import MovieLayout
        except ImportError:
            from host.movie_models import MovieLayout
        movie_conf = self.settings.get("movie", {})
        return MovieLayout.from_dict(movie_conf)

    def set_movie_layout(self, layout_dict: dict) -> Tuple[bool, Optional[str]]:
        try:
            from movie_models import MovieLayout
        except ImportError:
            from host.movie_models import MovieLayout
        try:
            layout = MovieLayout.from_dict(layout_dict)
            ok, err = layout.validate(self.led_count)
            if not ok:
                return False, err
            movie_conf = self.settings.setdefault("movie", {})
            movie_conf.update(layout.to_dict())
            self.save()
            return True, None
        except Exception as e:
            return False, str(e)

    def set_movie_music_sync(self, sync_music: bool) -> bool:
        movie_conf = self.settings.setdefault("movie", {})
        movie_conf["sync_music"] = bool(sync_music)
        self.save()
        return True

    def set_movie_monitor(self, monitor_index: int) -> bool:
        movie_conf = self.settings.setdefault("movie", {})
        movie_conf["monitor_index"] = max(1, int(monitor_index))
        self.save()
        return True

    def get_movie_settings(self) -> dict:
        return self.settings.get("movie", {})


    def set_movie_settings(self, settings_dict: dict) -> Tuple[bool, Optional[str]]:
        try:
            from movie_models import MovieSettings
        except ImportError:
            from host.movie_models import MovieSettings
        try:
            movie_conf = self.settings.setdefault("movie", {})
            movie_conf.update(settings_dict)
            # Re-validate layout
            layout = self.get_movie_layout()
            ok, err = layout.validate(self.led_count)
            if not ok:
                return False, err
            self.save()
            return True, None
        except Exception as e:
            return False, str(e)

    def get_custom_effect(self) -> str:
        return self.settings.get("custom", {}).get("effect", "rainfall")

    def set_custom_effect(self, effect_name: str) -> bool:
        try:
            from custom_effects import DEFAULT_EFFECT_CONFIGS
        except ImportError:
            from host.custom_effects import DEFAULT_EFFECT_CONFIGS

        effect = str(effect_name).lower()
        if effect not in DEFAULT_EFFECT_CONFIGS:
            return False
        custom_conf = self.settings.setdefault("custom", {})
        custom_conf["effect"] = effect
        configs = custom_conf.setdefault("configs", {})
        if effect not in configs:
            configs[effect] = dict(DEFAULT_EFFECT_CONFIGS.get(effect, {}))
        custom_conf["config"] = dict(configs[effect])
        cfg = custom_conf["config"]
        if "color" in cfg and isinstance(cfg["color"], dict):
            custom_conf["r"] = cfg["color"].get("r", custom_conf.get("r", 255))
            custom_conf["g"] = cfg["color"].get("g", custom_conf.get("g", 255))
            custom_conf["b"] = cfg["color"].get("b", custom_conf.get("b", 255))
        self.save()
        return True

    def get_custom_config(self, effect_name: Optional[str] = None) -> dict:
        try:
            from custom_effects import DEFAULT_EFFECT_CONFIGS
        except ImportError:
            from host.custom_effects import DEFAULT_EFFECT_CONFIGS

        effect = str(effect_name).lower() if effect_name else self.get_custom_effect()
        custom_conf = self.settings.get("custom", {})
        configs = custom_conf.get("configs", {})
        if effect in configs:
            return dict(configs[effect])
        return dict(DEFAULT_EFFECT_CONFIGS.get(effect, {}))

    def set_custom_config(self, effect_name: str, config_dict: dict) -> Tuple[bool, Optional[str]]:
        try:
            from custom_effects import DEFAULT_EFFECT_CONFIGS
        except ImportError:
            from host.custom_effects import DEFAULT_EFFECT_CONFIGS

        effect = str(effect_name).lower()
        if effect not in DEFAULT_EFFECT_CONFIGS:
            return False, f"Unknown effect '{effect_name}'"
        if not isinstance(config_dict, dict):
            return False, "Config must be a dictionary"

        custom_conf = self.settings.setdefault("custom", {})
        configs = custom_conf.setdefault("configs", {})
        eff_cfg = configs.setdefault(effect, dict(DEFAULT_EFFECT_CONFIGS.get(effect, {})))
        eff_cfg.update(config_dict)

        if custom_conf.get("effect") == effect:
            custom_conf["config"] = dict(eff_cfg)
            if "color" in eff_cfg and isinstance(eff_cfg["color"], dict):
                custom_conf["r"] = eff_cfg["color"].get("r", custom_conf.get("r", 255))
                custom_conf["g"] = eff_cfg["color"].get("g", custom_conf.get("g", 255))
                custom_conf["b"] = eff_cfg["color"].get("b", custom_conf.get("b", 255))

        self.save()
        return True, None

    def get_custom_settings(self) -> dict:
        return self.settings.get("custom", {})

    def get_developer_settings(self) -> dict:
        return dict(self.settings.get("developer", {}))

    def get_developer_zones(self) -> dict:
        return dict(self.settings.get("developer", {}).get("zones", {}))

    def get_developer_layout(self):
        try:
            from developer_models import DeveloperLayout
        except ImportError:
            from host.developer_models import DeveloperLayout
        zones_data = self.get_developer_zones()
        return DeveloperLayout.from_dict(zones_data, total_leds=self.led_count)

    def set_developer_zones(self, zones_dict: dict) -> Tuple[bool, Optional[str]]:
        try:
            from developer_models import DeveloperLayout
        except ImportError:
            from host.developer_models import DeveloperLayout

        if not isinstance(zones_dict, dict):
            return False, "Zones must be a dictionary mapping zone names to zone data"

        layout = DeveloperLayout.from_dict(zones_dict, total_leds=self.led_count)
        valid, err = layout.validate()
        if not valid:
            return False, err

        dev_conf = self.settings.setdefault("developer", {})
        dev_conf["zones"] = layout.to_dict()
        self.save()
        return True, None

    def set_developer_settings(self, settings_dict: dict) -> Tuple[bool, Optional[str]]:
        if not isinstance(settings_dict, dict):
            return False, "Settings must be a dictionary"

        dev_conf = self.settings.setdefault("developer", {})
        if "zones" in settings_dict:
            valid, err = self.set_developer_zones(settings_dict["zones"])
            if not valid:
                return False, err

        if "smoothing" in settings_dict:
            try:
                dev_conf["smoothing"] = max(0.0, min(1.0, float(settings_dict["smoothing"])))
            except (ValueError, TypeError):
                return False, "Invalid smoothing value"

        if "brightness_limit" in settings_dict:
            try:
                dev_conf["brightness_limit"] = max(0.0, min(1.0, float(settings_dict["brightness_limit"])))
            except (ValueError, TypeError):
                return False, "Invalid brightness_limit value"

        self.save()
        return True, None

