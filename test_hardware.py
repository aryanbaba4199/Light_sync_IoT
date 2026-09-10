import serial
import time
import struct

def test_esp32():
    print("Opening serial port...")
    try:
        ser = serial.Serial('/dev/cu.usbserial-0001', 115200, timeout=1)
        ser.dtr = False
        ser.rts = False
        time.sleep(2) # Wait for boot
        
        print("Sending WHITE...")
        # 0x55, R, G, B, Brightness
        packet = bytearray([0x55, 255, 255, 255, 255])
        ser.write(packet)
        time.sleep(1)
        
        print("Sending RED...")
        packet = bytearray([0x55, 255, 0, 0, 255])
        ser.write(packet)
        time.sleep(1)
        
        print("Sending GREEN...")
        packet = bytearray([0x55, 0, 255, 0, 255])
        ser.write(packet)
        time.sleep(1)
        
        print("Sending BLUE...")
        packet = bytearray([0x55, 0, 0, 255, 255])
        ser.write(packet)
        time.sleep(1)
        
        print("Sending OFF...")
        packet = bytearray([0x55, 0, 0, 0, 0])
        ser.write(packet)
        time.sleep(0.5)
        
        ser.close()
        print("Done.")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == '__main__':
    test_esp32()
