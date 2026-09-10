import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/analyzers/screen_analyzer.py', 'r') as f:
    content = f.read()

old = """                # Send to engine
                self.lighting_engine.set_ambient_color(r, g, b)"""

new = """                # Calculate brightness intensity based on screen lightness (average of RGB)
                intensity = min(1.0, max(r, max(g, b)) / 255.0)
                
                # Send to engine
                self.lighting_engine.set_ambient_color(r, g, b)
                self.lighting_engine.set_ambient_brightness(intensity)"""

content = content.replace(old, new)

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/analyzers/screen_analyzer.py', 'w') as f:
    f.write(content)
