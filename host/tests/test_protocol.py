import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from transports import SerialTransport, UDPTransport

class TestProtocol(unittest.TestCase):
    def test_serial_packet_format(self):
        transport = SerialTransport(port="DUMMY")
        transport.ser = MagicMock()
        transport.ser.is_open = True
        
        # Override lock and connect logic for test
        transport.is_connected = lambda: True
        
        transport.send_state(255, 128, 0, 50)
        
        # Verify write was called with exactly 5 bytes: [0x55, 255, 128, 0, 50]
        transport.ser.write.assert_called_once_with(b'\x55\xff\x80\x00\x32')

    def test_udp_packet_format(self):
        transport = UDPTransport(ip="127.0.0.1", port=4210)
        transport.sock = MagicMock()
        
        transport.send_state(10, 20, 30, 255)
        
        transport.sock.sendto.assert_called_once_with(b'\x55\x0a\x14\x1e\xff', ("127.0.0.1", 4210))

if __name__ == '__main__':
    unittest.main()
