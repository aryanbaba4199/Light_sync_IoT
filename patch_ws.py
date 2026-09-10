import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/api/websocket_server.py', 'r') as f:
    content = f.read()

# Fix brightness broadcast reading
content = content.replace('"brightness": self.engine.user_intensity,', '"brightness": self.engine.user_brightness,')

# Fix brightness setting
content = content.replace('self.engine.set_ambient_brightness(val)', 'self.engine.set_user_brightness(val)')

# Add missing import for asyncio if needed
if "import asyncio" not in content:
    content = "import asyncio\n" + content

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/api/websocket_server.py', 'w') as f:
    f.write(content)
