import time
import sys
from transports import SerialTransport

def run_hardware_test():
    print("--- Starting Direct Hardware Pipeline Test ---")
    
    transport = SerialTransport()
    
    print("Connecting transport...")
    if not transport.connect():
        print("Failed to connect to ESP32! Check USB connection.")
        sys.exit(1)
        
    print(f"Transport connected on {transport.port}")
    print("Bypassing Lighting Engine smoothing for raw hardware test.\n")
    
    try:
        # User requested exact test sequence:
        # [0x55, 255, 0, 0, 128] -> RED
        # [0x55, 0, 255, 0, 128] -> GREEN
        # [0x55, 0, 0, 255, 128] -> BLUE
        # [0x55, 255, 255, 255, 128] -> WHITE
        # [0x55, 0, 0, 0, 0] -> OFF
        
        test_sequence = [
            ("RED", 255, 0, 0, 128),
            ("GREEN", 0, 255, 0, 128),
            ("BLUE", 0, 0, 255, 128),
            ("WHITE", 255, 255, 255, 128),
            ("OFF", 0, 0, 0, 0),
        ]
        
        for name, r, g, b, brightness in test_sequence:
            print(f"Testing {name}: [0x55, {r}, {g}, {b}, {brightness}]")
            # Send exactly what the user requested, raw and unfiltered
            transport.send_state(r, g, b, brightness)
            time.sleep(2.0)
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        print("\nCleaning up...")
        # Send OFF before disconnecting
        transport.send_state(0, 0, 0, 0)
        transport.disconnect()
        print("Done.")

if __name__ == "__main__":
    run_hardware_test()
