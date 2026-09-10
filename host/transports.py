import serial
import serial.tools.list_ports
import socket
import time
import threading
from typing import List, Dict, Tuple, Optional

def encode_zone_packet(zones: List[dict]) -> bytes:
    """
    Protocol V2 Zone Packet:
    Header: 0x56
    Count: uint8 (number of zones)
    Per zone:
      start_hi, start_lo (uint16 big-endian, 0-based index)
      end_hi, end_lo (uint16 big-endian, 0-based index)
      r, g, b (uint8)
    Checksum: XOR of all bytes from header through end of zones
    """
    data = bytearray([0x56, len(zones)])
    for z in zones:
        s = int(z.get("start", 0))
        e = int(z.get("end", 0))
        r = max(0, min(255, int(z.get("r", 0))))
        g = max(0, min(255, int(z.get("g", 0))))
        b = max(0, min(255, int(z.get("b", 0))))
        data.extend([
            (s >> 8) & 0xFF, s & 0xFF,
            (e >> 8) & 0xFF, e & 0xFF,
            r, g, b
        ])
    checksum = 0
    for b in data:
        checksum ^= b
    data.append(checksum)
    return bytes(data)

def encode_indexed_packet(r: int, g: int, b: int, indices: List[int]) -> bytes:
    """
    Protocol V2 Sparse Indexed Packet (for random distribution):
    Header: 0x57
    Color: r, g, b (uint8)
    Count: count_hi, count_lo (uint16 big-endian)
    Indices: [idx_hi, idx_lo] * count (uint16 big-endian, 0-based index)
    Checksum: XOR of all bytes
    """
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    count = len(indices)
    data = bytearray([0x57, r, g, b, (count >> 8) & 0xFF, count & 0xFF])
    for idx in indices:
        data.extend([(idx >> 8) & 0xFF, idx & 0xFF])
    checksum = 0
    for byte in data:
        checksum ^= byte
    data.append(checksum)
    return bytes(data)

class BaseTransport:
    def connect(self) -> bool:
        raise NotImplementedError
        
    def disconnect(self):
        raise NotImplementedError
        
    def is_connected(self) -> bool:
        raise NotImplementedError
        
    def send_state(self, r: int, g: int, b: int, brightness: int) -> bool:
        raise NotImplementedError

    def send_zones(self, zones: List[dict]) -> bool:
        return True

    def send_frame(self, led_frame: List[Tuple[int, int, int]]) -> bool:
        return True

class SerialTransport(BaseTransport):
    def __init__(self, port=None, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.lock = threading.Lock()
        self.last_connect_attempt = 0
        self.last_log_time = 0
        self.last_sent_payload: Optional[bytes] = None
        self.last_sent_time = 0.0
        
    def _auto_discover_port(self):
        ports = serial.tools.list_ports.comports()
        ports = sorted(ports, key=lambda p: 0 if p.device.startswith('/dev/cu.') else 1)
        for p in ports:
            if "Bluetooth" in p.device or "debug-console" in p.device or "MacBook" in p.device:
                continue
            if "SLAB_USBtoUART" in p.device or "usbserial" in p.device or "CH340" in p.description or "UART" in p.description or "CP210" in p.description:
                return p.device
        for p in ports:
            if "Bluetooth" not in p.device and "debug-console" not in p.device and "MacBook" not in p.device and p.device.startswith("/dev/cu."):
                return p.device
        return None

    def connect(self) -> bool:
        with self.lock:
            if self.ser and self.ser.is_open:
                return True
                
            now = time.time()
            if now - self.last_connect_attempt < 2:
                return False
            self.last_connect_attempt = now
                
            port_to_use = self.port or self._auto_discover_port()
            if not port_to_use:
                return False
                
            try:
                self.ser = serial.Serial()
                self.ser.port = port_to_use
                self.ser.baudrate = self.baudrate
                self.ser.timeout = 1
                self.ser.write_timeout = 0.1
                self.ser.exclusive = True
                self.ser.dtr = False
                self.ser.rts = False
                self.ser.open()
                time.sleep(2)
                self.port = port_to_use
                print(f"[SerialTransport] Discovered ESP32... Selected {self.port}")
                print(f"[SerialTransport] Connected")
                return True
            except Exception as e:
                print(f"Serial Connect Failed: {e}")
                self.ser = None
                self.port = None
                return False

    def disconnect(self):
        with self.lock:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = None
            self.last_sent_payload = None
            print("Serial Transport Disconnected")

    def is_connected(self) -> bool:
        ser = self.ser
        return ser is not None and getattr(ser, "is_open", False)

    def _write_bytes(self, payload: bytes) -> bool:
        now = time.time()
        # Change detection with 1.0s heartbeat rate limit
        if payload == self.last_sent_payload and (now - self.last_sent_time) < 1.0:
            return True

        with self.lock:
            if not self.ser or not self.ser.is_open:
                return False
            try:
                self.ser.write(payload)
                self.last_sent_payload = payload
                self.last_sent_time = now
                return True
            except Exception as e:
                print(f"Connection lost during serial write: {e}. Disconnecting.")
                try:
                    self.ser.close()
                except:
                    pass
                self.ser = None
                self.port = None
                self.last_sent_payload = None
                return False

    def send_state(self, r: int, g: int, b: int, brightness: int) -> bool:
        """Protocol V1 Legacy Packet (5 bytes)"""
        if not self.is_connected():
            if not self.connect():
                return False
                
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))
        brightness = max(0, min(255, int(brightness)))
        
        payload = bytes([0x55, r, g, b, brightness])
        return self._write_bytes(payload)

    def send_zones(self, zones: List[dict]) -> bool:
        """Protocol V2 Zone Packet (0x56)"""
        if not self.is_connected():
            if not self.connect():
                return False

        # Filter continuous zones vs random zones
        continuous_zones = [z for z in zones if z.get("distribution") != "random"]
        random_zones = [z for z in zones if z.get("distribution") == "random"]

        # Send continuous zones
        if continuous_zones or not random_zones:
            payload = encode_zone_packet(continuous_zones)
            if not self._write_bytes(payload):
                return False

        # Send any random zones as indexed sparse packets (0x57)
        for rz in random_zones:
            from music_models import generate_deterministic_leds
            indices = generate_deterministic_leds(rz["start"] + 1, rz["end"] + 1, rz.get("seed", 42))
            indexed_payload = encode_indexed_packet(rz["r"], rz["g"], rz["b"], indices)
            if not self._write_bytes(indexed_payload):
                return False

        return True

    def hard_reset_hardware(self) -> bool:
        """
        Forces a physical hardware reset of the ESP32 via serial DTR/RTS lines and sends
        the reset protocol packet [0x58, 0xA5, 0x5A, 0x58].
        Works identically to pressing the EN/RST physical button on the ESP32 board!
        """
        with self.lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(bytes([0x58, 0xA5, 0x5A, 0x58]))
                    time.sleep(0.05)
                except Exception as e:
                    print(f"[SerialTransport] Soft reset packet error: {e}")

            try:
                if not self.ser or not self.ser.is_open:
                    port_to_use = self.port or self._auto_discover_port()
                    if not port_to_use:
                        return False
                    s = serial.Serial()
                    s.port = port_to_use
                    s.baudrate = self.baudrate
                    s.timeout = 1
                    s.open()
                    s.dtr = False
                    s.rts = True
                    time.sleep(0.1)
                    s.rts = False
                    time.sleep(0.8)
                    s.close()
                    return True
                else:
                    self.ser.dtr = False
                    self.ser.rts = True
                    time.sleep(0.1)
                    self.ser.rts = False
                    time.sleep(0.8)
                    try:
                        self.ser.reset_input_buffer()
                        self.ser.reset_output_buffer()
                    except:
                        pass
                    self.last_sent_payload = None
                    return True
            except Exception as e:
                print(f"[SerialTransport] Hardware reset error: {e}")
                return False

class UDPTransport(BaseTransport):
    def __init__(self, ip, port=4210):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.connected = True

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
    Consumes hardware states and routes them virtually back to the DevLights Desktop API.
    """
    def __init__(self):
        self.connected = False
        self.last_state = {"r": 0, "g": 0, "b": 0, "brightness": 0}
        self.last_zones: List[dict] = []
        self.last_frame: List[Tuple[int, int, int]] = []

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

    def send_zones(self, zones: List[dict]) -> bool:
        self.last_zones = zones
        return True

    def send_frame(self, led_frame: List[Tuple[int, int, int]]) -> bool:
        self.last_frame = led_frame
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
        return True

    def get_active_transport_name(self) -> str:
        return self._active_transport

    def get_last_virtual_state(self):
        return self.virtual_transport.last_state

    def send_state(self, r: int, g: int, b: int, brightness: int) -> bool:
        mode = self.app_state.output_mode
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
                return self.serial_transport.send_state(r, g, b, brightness)
            else:
                self._active_transport = "virtual"
                now = time.time()
                if now - self.last_attempt > 5:
                    self.last_attempt = now
                    if self.serial_transport.connect():
                        self._active_transport = "serial"
                        return self.serial_transport.send_state(r, g, b, brightness)
                return True
        return False

    def send_zones(self, zones: List[dict]) -> bool:
        mode = self.app_state.output_mode
        self.virtual_transport.send_zones(zones)

        if mode == "virtual":
            if self.serial_transport.is_connected():
                self.serial_transport.disconnect()
            self._active_transport = "virtual"
            return True

        elif mode == "esp32":
            self._active_transport = "serial"
            return self.serial_transport.send_zones(zones)

        elif mode == "auto":
            if self.serial_transport.is_connected():
                self._active_transport = "serial"
                return self.serial_transport.send_zones(zones)
            else:
                self._active_transport = "virtual"
                now = time.time()
                if now - self.last_attempt > 5:
                    self.last_attempt = now
                    if self.serial_transport.connect():
                        self._active_transport = "serial"
                        return self.serial_transport.send_zones(zones)
                return True
        return False

    def send_frame(self, led_frame: List[Tuple[int, int, int]]) -> bool:
        self.virtual_transport.send_frame(led_frame)
        return True

    def hard_reset_hardware(self) -> bool:
        return self.serial_transport.hard_reset_hardware()
