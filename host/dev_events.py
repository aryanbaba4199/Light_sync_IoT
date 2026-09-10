import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Any

try:
    from developer_models import DeveloperEventType, DeveloperPriority
    from developer_engine import DeveloperEventManager
except ImportError:
    from host.developer_models import DeveloperEventType, DeveloperPriority
    from host.developer_engine import DeveloperEventManager

class DevEventHandler:
    """
    HTTP event listener for external developer activity (e.g. IDE plugins, git hooks, CI/CD).
    Validates event payload against DeveloperEventType and delegates state transitions
    to DeveloperEventManager. Contains NO rendering logic or hardcoded colors.
    """
    def __init__(self, engine_or_manager: Any, port: int = 9999):
        if hasattr(engine_or_manager, "developer_event_manager"):
            self.manager: Optional[DeveloperEventManager] = engine_or_manager.developer_event_manager
            self.engine = engine_or_manager
        elif isinstance(engine_or_manager, DeveloperEventManager) or hasattr(engine_or_manager, "handle_event"):
            self.manager = engine_or_manager
            self.engine = None
        else:
            self.manager = None
            self.engine = engine_or_manager
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        manager = self.manager
        engine = self.engine

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                active_mgr = manager
                if active_mgr is None and engine and hasattr(engine, "developer_event_manager"):
                    active_mgr = engine.developer_event_manager
                
                if active_mgr:
                    cur_state = active_mgr.get_state().value
                    cur_event = active_mgr.get_active_event()
                    resp = {
                        "status": "ok",
                        "developer_state": cur_state,
                        "active_event": cur_event.to_dict() if cur_event else None
                    }
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(resp).encode('utf-8'))
                else:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok","message":"DevEventHandler running"}\n')

            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    raw_event = data.get("event") or data.get("event_type", "")
                    if not raw_event:
                        self.send_response(400)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(b'{"error":"missing event field"}\n')
                        return

                    # Priority conversion if specified
                    raw_priority = data.get("priority")
                    priority = None
                    if raw_priority is not None:
                        if isinstance(raw_priority, int):
                            priority = DeveloperPriority(raw_priority)
                        elif isinstance(raw_priority, str):
                            priority = DeveloperPriority[raw_priority.upper()]

                    duration = data.get("duration")
                    if duration is not None:
                        duration = float(duration)

                    metadata = data.get("metadata", {})

                    active_mgr = manager
                    if active_mgr is None and engine and hasattr(engine, "developer_event_manager"):
                        active_mgr = engine.developer_event_manager

                    if active_mgr:
                        success, err, result = active_mgr.handle_event(
                            event_input=raw_event,
                            priority=priority,
                            duration=duration,
                            metadata=metadata
                        )
                        if success:
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({"status": "ok", **result}).encode('utf-8'))
                        else:
                            self.send_response(400)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({"error": err or "unknown event type"}).encode('utf-8'))
                    elif engine and hasattr(engine, "trigger_developer_event"):
                        success, err, result = engine.trigger_developer_event(
                            event_input=raw_event,
                            priority=priority,
                            duration=duration,
                            metadata=metadata
                        )
                        if success:
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({"status": "ok", **result}).encode('utf-8'))
                        else:
                            self.send_response(400)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({"error": err or "unknown event type"}).encode('utf-8'))
                    else:
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(b'{"error":"no developer manager configured"}\n')

                except Exception as e:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
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
