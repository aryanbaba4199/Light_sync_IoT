import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/lighting_engine.py', 'r') as f:
    content = f.read()

loop_start = """    def _render_loop(self):
        target_fps = 30 # Increased to 30 FPS for ambient lighting
        frame_time = 1.0 / target_fps
        
        while self.running:
            start_time = time.time()"""

new_loop_start = """    def _render_loop(self):
        target_fps = 30 # Increased to 30 FPS for ambient lighting
        frame_time = 1.0 / target_fps
        
        last_wake_time = time.time()
        
        while self.running:
            start_time = time.time()
            
            # MACOS SLEEP DETECTION HACK
            # If the loop pauses for more than 3 seconds, it means the OS went to sleep!
            if start_time - last_wake_time > 3.0:
                print("WOKE FROM SLEEP! Forcing transport reconnect to grab new USB handle...")
                if self.transport:
                    self.transport.disconnect()
            last_wake_time = start_time"""

content = content.replace(loop_start, new_loop_start)

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/lighting_engine.py', 'w') as f:
    f.write(content)
