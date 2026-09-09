import serial
import time
import threading

class SerialCommunicator:
    def __init__(self, port='/dev/tty.SLAB_USBtoUART', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connected = False
        self.lock = threading.Lock()
        
    def connect(self):
        with self.lock:
            if self.connected:
                return True
            try:
                self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
                time.sleep(2) # wait for ESP32 to reset after connection
                self.connected = True
                print(f"Connected to {self.port}")
                return True
            except serial.SerialException as e:
                print(f"Failed to connect: {e}")
                self.connected = False
                return False
            
    def disconnect(self):
        with self.lock:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.connected = False
            print("Disconnected")
        
    def send_command(self, r, g, b, brightness=1.0):
        if not self.connected:
            # Try to connect without blocking the main lock excessively
            if not self.connect():
                return False
                
        # Binary protocol: [0x55, R, G, B, Brightness_Int]
        bright_int = int(max(0.0, min(1.0, brightness)) * 255)
        payload = bytes([0x55, int(r), int(g), int(b), bright_int])
        
        with self.lock:
            if not self.connected:
                return False
            try:
                self.ser.write(payload)
                # No longer blocking with readline()! Fire and forget.
                return True
            except serial.SerialException:
                print("Connection lost while sending.")
                self.connected = False
                return False
