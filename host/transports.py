import serial
import serial.tools.list_ports
import socket
import time
import threading

class BaseTransport:
    def connect(self) -> bool:
        raise NotImplementedError
        
    def disconnect(self):
        raise NotImplementedError
        
    def is_connected(self) -> bool:
        raise NotImplementedError
        
    def send_state(self, r: int, g: int, b: int, brightness: int) -> bool:
        raise NotImplementedError

class SerialTransport(BaseTransport):
    def __init__(self, port=None, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.lock = threading.Lock()
        self.last_connect_attempt = 0
        self.last_log_time = 0
        
    def _auto_discover_port(self):
        ports = serial.tools.list_ports.comports()
        
        # Sort to prefer /dev/cu.* over /dev/tty.* on macOS
        ports = sorted(ports, key=lambda p: 0 if p.device.startswith('/dev/cu.') else 1)
        
        for p in ports:
            # Common USB-to-UART bridge identifiers for ESP32
            # Explicitly reject macOS internal/bluetooth ports
            if "Bluetooth" in p.device or "debug-console" in p.device or "MacBook" in p.device:
                continue
            if "SLAB_USBtoUART" in p.device or "usbserial" in p.device or "CH340" in p.description or "UART" in p.description or "CP210" in p.description:
                return p.device
                
        # If no strict match, find the first port that isn't a known internal port
        for p in ports:
            if "Bluetooth" not in p.device and "debug-console" not in p.device and "MacBook" not in p.device and p.device.startswith("/dev/cu."):
                return p.device
                
        return None

    def connect(self) -> bool:
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
                return False

    def disconnect(self):
        with self.lock:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = None
            print("Serial Transport Disconnected")

    def is_connected(self) -> bool:
        with self.lock:
            return self.ser is not None and self.ser.is_open

    def send_state(self, r: int, g: int, b: int, brightness: int) -> bool:
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
                return False

class UDPTransport(BaseTransport):
    def __init__(self, ip, port=4210):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.connected = True # UDP is connectionless

    def connect(self) -> bool:
        return True

    def disconnect(self):
        try:
            self.sock.close()
        except:
            pass

    def is_connected(self) -> bool:
        return True

    def send_state(self, r: int, g: int, b: int, brightness: int) -> bool:
        payload = bytes([0x55, r, g, b, brightness])
        try:
            self.sock.sendto(payload, (self.ip, self.port))
            return True
        except Exception as e:
            print(f"UDP send failed: {e}")
            return False

class VirtualTransport(BaseTransport):
    """
    Consumes hardware states but routes them virtually back to the DevLights Desktop API 
    so the user can see exactly what WOULD have gone to the physical LEDs.
    """
    def __init__(self):
        self.connected = False
        self.last_state = {"r": 0, "g": 0, "b": 0, "brightness": 0}

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected

    def send_state(self, r: int, g: int, b: int, brightness: int) -> bool:
        if not self.connected:
            return False
            
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))
        brightness = max(0, min(255, int(brightness)))
        
        self.last_state = {"r": r, "g": g, "b": b, "brightness": brightness}
        return True

class DynamicTransport(BaseTransport):
    def __init__(self, app_state):
        self.app_state = app_state
        self.serial_transport = SerialTransport(port=None, baudrate=115200)
        self.virtual_transport = VirtualTransport()
        self.virtual_transport.connect()
        self.last_attempt = 0
        self._active_transport = "virtual"
        
    def connect(self) -> bool:
        return True
        
    def disconnect(self):
        self.serial_transport.disconnect()
        self.virtual_transport.disconnect()
        
    def is_connected(self) -> bool:
        # We are always "connected" to the virtual transport
        # But we report what we're actually routing to
        return True

    def get_active_transport_name(self) -> str:
        return self._active_transport

    def get_last_virtual_state(self):
        return self.virtual_transport.last_state

    def send_state(self, r: int, g: int, b: int, brightness: int) -> bool:
        mode = self.app_state.output_mode
        
        # We always keep virtual updated so the UI always has state
        self.virtual_transport.send_state(r, g, b, brightness)
        
        if mode == "virtual":
            if self.serial_transport.is_connected():
                self.serial_transport.disconnect()
            self._active_transport = "virtual"
            return True
            
        elif mode == "esp32":
            self._active_transport = "serial"
            return self.serial_transport.send_state(r, g, b, brightness)
            
        elif mode == "auto":
            if self.serial_transport.is_connected():
                self._active_transport = "serial"
                # If connected, send to serial. If it fails, it will disconnect itself inside send_state.
                return self.serial_transport.send_state(r, g, b, brightness)
            else:
                self._active_transport = "virtual"
                # Throttle reconnect attempts to once every 5 seconds to avoid locking up the engine loop
                import time
                now = time.time()
                if now - self.last_attempt > 5:
                    self.last_attempt = now
                    if self.serial_transport.connect():
                        self._active_transport = "serial"
                        return self.serial_transport.send_state(r, g, b, brightness)
                
                return True
        
        return False
