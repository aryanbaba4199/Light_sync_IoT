import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/transports.py', 'r') as f:
    content = f.read()

content = content.replace("""                # Pulse DTR to force a clean reset into the sketch, then release
                self.ser.dtr = True
                time.sleep(0.1)
                self.ser.dtr = False""", "")

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/transports.py', 'w') as f:
    f.write(content)
