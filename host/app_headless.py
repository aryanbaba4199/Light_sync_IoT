import sys
import time
import asyncio
import threading
from transports import SerialTransport
from lighting_engine import LightingEngine
from app_state import AppState
from api.websocket_server import DevLightsAPI

def run_api(engine, app_state, analyzer_manager):
    api_server = DevLightsAPI(engine, app_state, analyzer_manager)
    asyncio.run(api_server.start_server())

def main():
    print("DevLights Headless Engine Starting...")
    
    # 1. Initialize State
    app_state = AppState(config_file="config.json")
    
    # 2. Discover & Initialize Hardware
    from transports import DynamicTransport
    transport = DynamicTransport(app_state)
    print("[Lifecycle] Transport initialized.")

    # 3. Start Lighting Engine
    engine = LightingEngine(transport=transport, app_state=app_state)
    print("[Lifecycle] Engine active.")
    
    # 3.5 Start Analyzers
    from analyzer_manager import AnalyzerManager
    analyzer_manager = AnalyzerManager(engine, app_state)
    # Perform initial check
    analyzer_manager.check_state()

    # 4. Start WebSocket API
    api_thread = threading.Thread(target=run_api, args=(engine, app_state, analyzer_manager), daemon=True)
    api_thread.start()

    print("[Lifecycle] Engine is fully operational.")

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[Lifecycle] Shutting down...")
        engine.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
