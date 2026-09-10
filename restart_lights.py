#!/usr/bin/env python3
"""
DevLights - One-Command Emergency Restart Utility
Restarts the ESP32 hardware, resets LED state, clears serial buffers,
and re-synchronizes the lighting engine without having to unplug SMPS or USB cables.

Usage:
    python3 restart_lights.py
"""
import sys
import time
import json
import serial
import serial.tools.list_ports

def auto_discover_esp32_port():
    ports = sorted(serial.tools.list_ports.comports(), key=lambda p: 0 if p.device.startswith('/dev/cu.') else 1)
    for p in ports:
        if any(x in p.device for x in ["Bluetooth", "debug-console", "MacBook"]):
            continue
        if any(x in p.device or x in (p.description or "") for x in ["SLAB_USBtoUART", "usbserial", "CH340", "CP210"]):
            return p.device
    for p in ports:
        if p.device.startswith("/dev/cu.") and not any(x in p.device for x in ["Bluetooth", "debug-console", "MacBook"]):
            return p.device
    return None

def direct_hardware_reset():
    port = auto_discover_esp32_port()
    if not port:
        print("[!] No ESP32 serial device found.")
        return False

    print(f"[*] Connecting directly to ESP32 on {port}...")
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        
        # 1. Send software reset packet
        try:
            ser.write(bytes([0x58, 0xA5, 0x5A, 0x58]))
            time.sleep(0.05)
        except:
            pass

        # 2. Pulse DTR/RTS to physically toggle ESP32 EN/RST pin
        print("[*] Pulsing hardware EN pin (DTR/RTS reset)...")
        ser.dtr = False
        ser.rts = True
        time.sleep(0.1)
        ser.rts = False
        time.sleep(0.8)

        # 3. Clear buffers & send blackout frame
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Send blackout packet (Protocol V1)
        ser.write(bytearray([0x55, 0, 0, 0, 0]))
        time.sleep(0.1)
        ser.close()
        print("[+] Direct ESP32 hardware reset successful!")
        return True
    except Exception as e:
        print(f"[-] Direct serial reset failed: {e}")
        return False

def restart_via_websocket():
    try:
        import asyncio
        import websockets
    except ImportError:
        return False

    async def _call_api():
        try:
            async with websockets.connect("ws://localhost:8765", open_timeout=1.5) as ws:
                await ws.recv() # Initial state
                print("[*] Sending restart_all command to DevLights Engine...")
                await ws.send(json.dumps({"type": "restart_all"}))
                
                # Wait for confirmation
                t0 = time.time()
                while time.time() - t0 < 3.0:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(msg)
                    if data.get("type") == "restart_complete":
                        print(f"[+] Engine confirmed: {data['payload'].get('message')}")
                        return True
                return True
        except Exception as e:
            return False

    try:
        return asyncio.run(_call_api())
    except Exception:
        return False

def main():
    print("=" * 60)
    print("DevLights - Hardware & Lighting System Restart Utility")
    print("=" * 60)
    
    # First attempt: Try sending command to the running background engine
    print("[*] Checking if DevLights Engine is running on port 8765...")
    if restart_via_websocket():
        print("[+] Successfully restarted all hardware, engine state, and LEDs!")
        print("=" * 60)
        sys.exit(0)

    # Fallback: Perform direct USB serial DTR/RTS hardware reset
    print("[!] Engine not responding or busy. Performing direct hardware reset...")
    if direct_hardware_reset():
        print("[+] ESP32 micro-controller rebooted and LED strip cleared.")
        print("=" * 60)
        sys.exit(0)
    else:
        print("[-] Could not reset ESP32. Please check that the USB cable is securely connected.")
        sys.exit(1)

if __name__ == "__main__":
    main()
