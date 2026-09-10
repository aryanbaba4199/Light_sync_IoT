import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/transports.py', 'r') as f:
    content = f.read()

content = content.replace(
    "self.ser = serial.Serial(port_to_use, self.baudrate, timeout=1, write_timeout=0.1, exclusive=True)",
    "self.ser = serial.Serial(port_to_use, self.baudrate, timeout=1, write_timeout=0.1, exclusive=True)\n                self.ser.setDTR(False)\n                self.ser.setRTS(False)"
)

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/transports.py', 'w') as f:
    f.write(content)
