import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/analyzers/music_analyzer.py', 'r') as f:
    content = f.read()

mapping_code = '''                    # Map to RGB
                    r = int(self.bass_smooth * 255)
                    g = int(self.mid_smooth * 255)
                    b = int(self.treb_smooth * 255)
                    
                    # Boost RGB slightly to ensure vivid colors even at lower intensities
                    max_rgb = max(r, g, b, 1)
                    r = int((r / max_rgb) * 255) if r > 10 else 0
                    g = int((g / max_rgb) * 255) if g > 10 else 0
                    b = int((b / max_rgb) * 255) if b > 10 else 0'''

new_mapping_code = '''                    # Get custom colors from app_state if available
                    bass_col = {"r": 255, "g": 0, "b": 0}
                    mid_col = {"r": 0, "g": 255, "b": 0}
                    treb_col = {"r": 0, "g": 0, "b": 255}
                    
                    if self.engine and self.engine.app_state:
                        music_set = self.engine.app_state.settings.get("music", {})
                        bass_col = music_set.get("bass_color", bass_col)
                        mid_col = music_set.get("mid_color", mid_col)
                        treb_col = music_set.get("treb_color", treb_col)
                        
                    # Map to RGB using custom colors
                    bass_r = self.bass_smooth * bass_col["r"]
                    bass_g = self.bass_smooth * bass_col["g"]
                    bass_b = self.bass_smooth * bass_col["b"]
                    
                    mid_r = self.mid_smooth * mid_col["r"]
                    mid_g = self.mid_smooth * mid_col["g"]
                    mid_b = self.mid_smooth * mid_col["b"]
                    
                    treb_r = self.treb_smooth * treb_col["r"]
                    treb_g = self.treb_smooth * treb_col["g"]
                    treb_b = self.treb_smooth * treb_col["b"]
                    
                    r = min(255, int(bass_r + mid_r + treb_r))
                    g = min(255, int(bass_g + mid_g + treb_g))
                    b = min(255, int(bass_b + mid_b + treb_b))
                    
                    # Boost RGB slightly
                    max_rgb = max(r, g, b, 1)
                    r = int((r / max_rgb) * 255) if r > 10 else 0
                    g = int((g / max_rgb) * 255) if g > 10 else 0
                    b = int((b / max_rgb) * 255) if b > 10 else 0'''

content = content.replace(mapping_code, new_mapping_code)

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/analyzers/music_analyzer.py', 'w') as f:
    f.write(content)
