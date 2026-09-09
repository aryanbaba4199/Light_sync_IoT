import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from lighting_state import EventPriority

class DevEventHandler:
    def __init__(self, lighting_engine, port=9999):
        self.lighting_engine = lighting_engine
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        class Handler(BaseHTTPRequestHandler):
            engine = self.lighting_engine
            
            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    event_type = data.get("event", "").upper()
                    
                    # Define event mappings
                    # (R, G, B, duration_sec, is_critical)
                    event_map = {
                        "BUILD_STARTED": (0, 0, 255, 3.0, False),
                        "BUILD_SUCCESS": (0, 255, 0, 3.0, False),
                        "BUILD_FAILED": (255, 0, 0, 5.0, True),
                        "TEST_STARTED": (128, 0, 128, 3.0, False),
                        "TEST_SUCCESS": (0, 255, 0, 3.0, False),
                        "TEST_FAILED": (255, 0, 0, 5.0, True),
                        "DEPLOY_STARTED": (0, 255, 255, 3.0, False),
                        "DEPLOY_SUCCESS": (0, 255, 0, 3.0, False),
                        "DEPLOY_FAILED": (255, 0, 0, 5.0, True),
                        "WARNING": (255, 165, 0, 3.0, False),
                        "ERROR": (255, 0, 0, 5.0, True)
                    }
                    
                    if event_type in event_map:
                        r, g, b, duration, is_critical = event_map[event_type]
                        priority = EventPriority.CRITICAL_DEV_EVENT if is_critical else EventPriority.DEV_STATUS
                        self.engine.trigger_event(r, g, b, duration, priority)
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(b'{"status":"ok"}')
                    else:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'{"error":"unknown event type"}')
                        
                except Exception as e:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(f'{{"error":"{str(e)}"}}\n'.encode('utf-8'))
                    
            def log_message(self, format, *args):
                pass # Suppress HTTP logs

        self.server = HTTPServer(('', self.port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
