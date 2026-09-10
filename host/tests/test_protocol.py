import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from transports import SerialTransport, UDPTransport, encode_zone_packet, encode_indexed_packet

class TestProtocol(unittest.TestCase):
    def test_v1_serial_packet_format_regression(self):
        """Regression test for Protocol V1: exactly 5 bytes [0x55, R, G, B, Brightness]"""
        transport = SerialTransport(port="DUMMY")
        transport.ser = MagicMock()
        transport.ser.is_open = True
        transport.is_connected = lambda: True
        
        transport.send_state(255, 128, 0, 50)
        transport.ser.write.assert_called_once_with(b'\x55\xff\x80\x00\x32')

    def test_v1_udp_packet_format(self):
        transport = UDPTransport(ip="127.0.0.1", port=4210)
        transport.sock = MagicMock()
        
        transport.send_state(10, 20, 30, 255)
        transport.sock.sendto.assert_called_once_with(b'\x55\x0a\x14\x1e\xff', ("127.0.0.1", 4210))

    def test_v2_encode_zone_packet(self):
        """Verify Protocol V2 zone packet layout and XOR checksum."""
        zones = [
            {"start": 0, "end": 29, "r": 255, "g": 0, "b": 0},      # Bass: 0-29 Red
            {"start": 30, "end": 59, "r": 0, "g": 255, "b": 0}       # Vocal: 30-59 Green
        ]
        packet = encode_zone_packet(zones)
        # Expected:
        # [0x56] (header)
        # [0x02] (2 zones)
        # Zone 0: [0x00, 0x00, 0x00, 0x1D, 0xFF, 0x00, 0x00] (7 bytes)
        # Zone 1: [0x00, 0x1E, 0x00, 0x3B, 0x00, 0xFF, 0x00] (7 bytes)
        # Checksum: XOR of all previous bytes
        expected_len = 1 + 1 + (2 * 7) + 1  # 17 bytes
        self.assertEqual(len(packet), expected_len)
        self.assertEqual(packet[0], 0x56)
        self.assertEqual(packet[1], 2)
        
        # Verify checksum
        calc_checksum = 0
        for b in packet[:-1]:
            calc_checksum ^= b
        self.assertEqual(packet[-1], calc_checksum)

    def test_v2_encode_indexed_packet(self):
        """Verify Protocol V2 sparse indexed packet layout and XOR checksum."""
        indices = [0, 5, 12, 45, 299]
        packet = encode_indexed_packet(255, 100, 50, indices)
        # Expected:
        # [0x57, 255, 100, 50, 0, 5, (0,0), (0,5), (0,12), (0,45), (1, 43), checksum]
        expected_len = 1 + 3 + 2 + (len(indices) * 2) + 1 # 17 bytes
        self.assertEqual(len(packet), expected_len)
        self.assertEqual(packet[0], 0x57)
        self.assertEqual(packet[1:4], bytes([255, 100, 50]))
        self.assertEqual(packet[4:6], bytes([0x00, 0x05]))

        # Verify checksum
        calc_checksum = 0
        for b in packet[:-1]:
            calc_checksum ^= b
        self.assertEqual(packet[-1], calc_checksum)

    def test_v2_serial_send_zones(self):
        transport = SerialTransport(port="DUMMY")
        transport.ser = MagicMock()
        transport.ser.is_open = True
        transport.is_connected = lambda: True

        zones = [{"start": 0, "end": 29, "r": 255, "g": 0, "b": 0, "distribution": "zone"}]
        transport.send_zones(zones)

        transport.ser.write.assert_called_once()
        sent_bytes = transport.ser.write.call_args[0][0]
        self.assertEqual(sent_bytes[0], 0x56)
        self.assertEqual(sent_bytes[1], 1)

if __name__ == '__main__':
    unittest.main()
