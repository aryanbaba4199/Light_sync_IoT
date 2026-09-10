import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/transports.py', 'r') as f:
    content = f.read()

content = content.replace("self.lock = threading.Lock()", "self.lock = threading.Lock()\n        self.last_connect_attempt = 0")

old_connect = """    def connect(self) -> bool:
        with self.lock:
            if self.ser and self.ser.is_open:
                return True
                
            port_to_use = self.port or self._auto_discover_port()
            if not port_to_use:
                return False
                
            try:
                # Use exclusive=True to prevent multiple processes from opening the same port on macOS
                self.ser = serial.Serial(port_to_use, self.baudrate, timeout=1, write_timeout=0.1, exclusive=True)
                time.sleep(2) # Reset delay for ESP32
                self.port = port_to_use
                print(f"Serial Transport Connected: {self.port}")
                return True
            except serial.SerialException as e:
                print(f"Serial Connect Failed: {e}")
                self.ser = None
                self.port = None # Clear cached port so we can re-discover
                return False"""

new_connect = """    def connect(self) -> bool:
        with self.lock:
            if self.ser and self.ser.is_open:
                return True
                
            import time
            now = time.time()
            if now - self.last_connect_attempt < 2:
                return False
            self.last_connect_attempt = now
                
            port_to_use = self.port or self._auto_discover_port()
            if not port_to_use:
                return False
                
            try:
                # Use exclusive=True to prevent multiple processes from opening the same port on macOS
                self.ser = serial.Serial(port_to_use, self.baudrate, timeout=1, write_timeout=0.1, exclusive=True)
                time.sleep(2) # Reset delay for ESP32
                self.port = port_to_use
                print(f"[SerialTransport] Discovered ESP32... Selected {self.port}")
                print(f"[SerialTransport] Connected")
                return True
            except Exception as e:
                print(f"Serial Connect Failed: {e}")
                self.ser = None
                self.port = None # Clear cached port so we can re-discover
                return False"""

content = content.replace(old_connect, new_connect)

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/transports.py', 'w') as f:
    f.write(content)
