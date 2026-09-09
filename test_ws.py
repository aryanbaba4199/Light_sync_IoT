import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://127.0.0.1:8765"
    async with websockets.connect(uri) as websocket:
        # Listen for the initial broadcast
        state = await websocket.recv()
        print("Initial state:", state)
        
        # Send set_mode
        req = {
            "type": "set_mode",
            "payload": {"mode": "custom"}
        }
        await websocket.send(json.dumps(req))
        print("Sent set_mode custom")
        
        # Listen for reply
        reply = await websocket.recv()
        print("Reply:", reply)

asyncio.run(test_ws())
