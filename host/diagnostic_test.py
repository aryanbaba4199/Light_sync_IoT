import asyncio
import websockets
import json

async def send_cmd(ws, msg_type, payload):
    print(f"-> SEND {msg_type}: {payload}")
    await ws.send(json.dumps({"version": 1, "type": msg_type, "payload": payload}))
    await asyncio.sleep(1.0) # wait 1s between commands to let user observe

async def run_test():
    uri = "ws://127.0.0.1:8765"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print("Connected! Waiting for initial state...")
            
            print("\n--- STARTING TEST SEQUENCE ---")
            
            # 1. set_output_mode = esp32
            await send_cmd(ws, "set_output_mode", {"output_mode": "esp32"})
            
            # Switch to custom mode so we can manually set color
            await send_cmd(ws, "set_mode", {"mode": "custom"})
            
            # 2. power = ON
            await send_cmd(ws, "set_power", {"power_on": True})
            
            # 3 & 4. set_color = RED, brightness = 100
            await send_cmd(ws, "set_color", {"r": 255, "g": 0, "b": 0})
            await send_cmd(ws, "set_brightness", {"value": 1.0})
            print("\n[OBSERVE] Should be RED, Brightness 100%. Press Enter to continue...")
            
            # 5. brightness = 50
            await send_cmd(ws, "set_brightness", {"value": 0.5})
            print("\n[OBSERVE] Should be visibly dimmer (50%). Press Enter to continue...")
            
            # 6. brightness = 25
            await send_cmd(ws, "set_brightness", {"value": 0.25})
            print("\n[OBSERVE] Should be visibly dimmer (25%). Press Enter to continue...")
            
            # 7. brightness = 0
            await send_cmd(ws, "set_brightness", {"value": 0.0})
            print("\n[OBSERVE] Should be completely OFF. Press Enter to continue...")
            
            # 8. brightness = 100
            await send_cmd(ws, "set_brightness", {"value": 1.0})
            print("\n[OBSERVE] Should be RED and bright again. Press Enter to continue...")
            
            # 9. set_color = GREEN
            await send_cmd(ws, "set_color", {"r": 0, "g": 255, "b": 0})
            print("\n[OBSERVE] Should be GREEN. Press Enter to continue...")
            
            # 10. set_color = BLUE
            await send_cmd(ws, "set_color", {"r": 0, "g": 0, "b": 255})
            print("\n[OBSERVE] Should be BLUE. Press Enter to continue...")
            
            # 11. power = OFF
            await send_cmd(ws, "set_power", {"power_on": False})
            print("\n[OBSERVE] Should be completely OFF (Power OFF). Press Enter to continue...")
            
            # 12. power = ON
            await send_cmd(ws, "set_power", {"power_on": True})
            print("\n[OBSERVE] Should be restored to BLUE 100%. Press Enter to continue...")
            
            print("\n--- TEST SEQUENCE COMPLETE ---")
            
    except Exception as e:
        print(f"Failed to connect or send: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
