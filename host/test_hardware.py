import time
from transports import SerialTransport
from lighting_engine import LightingEngine
from app_state import AppState

def run_hardware_test():
    print("--- Starting Hardware Pipeline Test ---")
    
    # 1. Initialize State and Transport
    app_state = AppState()
    transport = SerialTransport()
    
    print("Connecting transport...")
    if not transport.connect():
        print("Failed to connect to ESP32! Check USB connection and ensure no other process (like pio monitor) is holding the port.")
        return
        
    print(f"Transport connected on {transport.port}")
    
    # 2. Initialize and start Engine
    engine = LightingEngine(transport, app_state)
    print("Engine started. Commencing color cycle...\n")
    
    try:
        # We simulate the exact states requested.
        # Since LightingEngine interpolates over time, we use a solid brightness (1.0) and push absolute colors.
        # Note: We must wait a brief moment for the thread to fully spool and push the initial frames.
        
        test_sequence = [
            ("RED", 255, 0, 0, 1.0),
            ("GREEN", 0, 255, 0, 1.0),
            ("BLUE", 0, 0, 255, 1.0),
            ("WHITE", 255, 255, 255, 1.0),
            ("OFF", 0, 0, 0, 0.0),
        ]
        
        for name, r, g, b, brightness in test_sequence:
            print(f"Testing {name}: [0x55, {r}, {g}, {b}, {int(brightness*255)}]")
            engine.set_ambient_color(r, g, b)
            engine.set_ambient_brightness(brightness)
            time.sleep(1.2) # Wait slightly >1s to allow smoothing to settle completely on the target
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        print("\nCleaning up...")
        engine.stop()
        transport.disconnect()
        print("Done. ESP32 should have diagnosed all 5 states.")

if __name__ == "__main__":
    run_hardware_test()
