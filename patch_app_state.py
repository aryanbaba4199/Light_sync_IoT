import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/app_state.py', 'r') as f:
    content = f.read()

# Add music_colors to the default music settings
old_music_settings = '"music": {"smoothing": 0.5, "brightness_limit": 1.0},'
new_music_settings = '''"music": {
                "smoothing": 0.5, 
                "brightness_limit": 1.0,
                "bass_color": {"r": 255, "g": 0, "b": 0},
                "mid_color": {"r": 0, "g": 255, "b": 0},
                "treb_color": {"r": 0, "g": 0, "b": 255}
            },'''

content = content.replace(old_music_settings, new_music_settings)

# Add update_music_colors method
method = '''    def set_output_mode(self, mode):
'''
new_method = '''    def update_music_colors(self, bass, mid, treb):
        if "music" in self.settings:
            if bass: self.settings["music"]["bass_color"] = bass
            if mid: self.settings["music"]["mid_color"] = mid
            if treb: self.settings["music"]["treb_color"] = treb
            self.save()

    def set_output_mode(self, mode):
'''

content = content.replace(method, new_method)

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/app_state.py', 'w') as f:
    f.write(content)
