import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/api/websocket_server.py', 'r') as f:
    content = f.read()

handler = '''            elif msg_type == "set_brightness":'''
new_handler = '''            elif msg_type == "set_music_colors":
                bass = payload.get("bass_color")
                mid = payload.get("mid_color")
                treb = payload.get("treb_color")
                self.app_state.update_music_colors(bass, mid, treb)
                logger.info("Music colors updated")
                await self.broadcast_state()

            elif msg_type == "set_brightness":'''

content = content.replace(handler, new_handler)

# Expose music settings in broadcast_state
state_payload = '''                "analyzers": self.analyzer_manager.get_status()'''
new_state_payload = '''                "analyzers": self.analyzer_manager.get_status(),
                        "music_settings": self.app_state.settings.get("music", {})'''
content = content.replace(state_payload, new_state_payload)

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/api/websocket_server.py', 'w') as f:
    f.write(content)
