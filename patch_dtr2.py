import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/transports.py', 'r') as f:
    content = f.read()

# Make sure we don't duplicate
content = content.replace("self.ser.setDTR(False)\n                self.ser.setRTS(False)", "")

# Insert properly
replacement = """self.ser = serial.Serial()
                self.ser.port = port_to_use
                self.ser.baudrate = self.baudrate
                self.ser.timeout = 1
                self.ser.write_timeout = 0.1
                self.ser.exclusive = True
                
                # CRITICAL FOR ESP32 ON MACOS:
                # Prevent pyserial from asserting DTR/RTS which forces the ESP32 into bootloader mode
                self.ser.dtr = False
                self.ser.rts = False
                
                self.ser.open()
                
                # Pulse DTR to force a clean reset into the sketch, then release
                self.ser.dtr = True
                time.sleep(0.1)
                self.ser.dtr = False
"""

content = content.replace(
    "self.ser = serial.Serial(port_to_use, self.baudrate, timeout=1, write_timeout=0.1, exclusive=True)",
    replacement
)

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/transports.py', 'w') as f:
    f.write(content)
