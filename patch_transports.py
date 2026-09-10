import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/transports.py', 'r') as f:
    content = f.read()

content = content.replace("self.ser = None\n        self.lock = threading.Lock()", "self.ser = None\n        self.lock = threading.Lock()\n        self.last_connect_attempt = 0")

connect_replacement = """    def connect(self) -> bool:
        with self.lock:
            if self.ser and self.ser.is_open:
                return True
                
            import time
            now = time.time()
            if now - self.last_connect_attempt < 3: # throttle reconnects
                return False
            self.last_connect_attempt = now
                
            port_to_use = self.port or self._auto_discover_port()
            if not port_to_use:
                return False
                
            try:
                self.ser = serial.Serial(port_to_use, self.baudrate, timeout=1, write_timeout=0.1, exclusive=True)
                time.sleep(2)
                self.port = port_to_use
                print(f"Serial Transport Connected: {self.port}")
                return True
            except Exception as e:
                print(f"Serial Connect Failed: {e}")
                self.ser = None
                self.port = None
                return False"""

# We need to replace the old connect method
import re
content = re.sub(r'    def connect\(self\) -> bool:.*?return False', connect_replacement, content, flags=re.DOTALL, count=1)

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/transports.py', 'w') as f:
    f.write(content)
