import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/transports.py', 'r') as f:
    content = f.read()

content = content.replace("self.last_connect_attempt = 0", "self.last_connect_attempt = 0\n        self.last_log_time = 0")

old_send = """    def send_state(self, r: int, g: int, b: int, brightness: int) -> bool:
        if not self.is_connected():
            if not self.connect():
                return False
                
        # Clamp values to 0-255 to ensure strict bounds and prevent exceptions
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))
        brightness = max(0, min(255, int(brightness)))
        
        # [MAGIC, R, G, B, Brightness]
        payload = bytes([0x55, r, g, b, brightness])
        
        with self.lock:
            if not self.ser or not self.ser.is_open:
                return False
            try:
                self.ser.write(payload)
                self.ser.flush() # Ensure it's pushed out
                return True
            except (serial.SerialException, serial.SerialTimeoutException) as e:
                print(f"Connection lost or timeout during serial write: {e}. Disconnecting.")
                self.ser.close()
                self.ser = None
                self.port = None # Clear cached port so we can re-discover
                return False"""

new_send = """    def send_state(self, r: int, g: int, b: int, brightness: int) -> bool:
        if not self.is_connected():
            if not self.connect():
                return False
                
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))
        brightness = max(0, min(255, int(brightness)))
        
        payload = bytes([0x55, r, g, b, brightness])
        
        import time
        now = time.time()
        if now - self.last_log_time > 1.0:
            print(f"[SerialTransport] SEND 55 {r:02X} {g:02X} {b:02X} {brightness:02X}")
            self.last_log_time = now
            
        with self.lock:
            if not self.ser or not self.ser.is_open:
                return False
            try:
                self.ser.write(payload)
                self.ser.flush()
                return True
            except Exception as e:
                print(f"Connection lost during serial write: {e}. Disconnecting.")
                self.ser.close()
                self.ser = None
                self.port = None
                return False"""

content = content.replace(old_send, new_send)

with open('/Users/aryandubey/project/personal/Automation/light_sync/host/transports.py', 'w') as f:
    f.write(content)
