import asyncio
import json
import websockets
import logging
from lighting_state import LightingState, EventPriority

import sys

# Setup simple logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("WebSocketAPI")

class DevLightsAPI:
    def __init__(self, engine, app_state, analyzer_manager, host="127.0.0.1", port=8765):
        self.engine = engine
        self.app_state = app_state
        self.analyzer_manager = analyzer_manager
        self.host = host
        self.port = port
        self.clients = set()
        self._loop = None

    def _get_led_frame_sample(self):
        if hasattr(self.engine, "led_frame") and self.engine.led_frame:
            frame = self.engine.led_frame
            total = len(frame)
            if total > 0:
                step = max(1, total // 60)
                return [[c[0], c[1], c[2]] for c in frame[::step][:60]]
        return []

    async def broadcast_state(self):
        """Sends the current state to all connected clients."""
        if not self.clients:
            return
            
        if hasattr(self.engine.transport, 'get_active_transport_name'):
            active_transport = self.engine.transport.get_active_transport_name()
            # If serial, the ESP32 is physically connected
            connected = self.engine.transport.serial_transport.is_connected()
        else:
            active_transport = self.engine.transport.__class__.__name__ if self.engine.transport else "none"
            connected = self.engine.transport.is_connected() if self.engine.transport else False

        movie_settings = self.app_state.get_movie_settings() if hasattr(self.app_state, "get_movie_settings") else {}
        try:
            from analyzers.screen_analyzer import ScreenAnalyzer
            movie_settings["available_monitors"] = ScreenAnalyzer.get_available_monitors()
        except Exception:
            movie_settings["available_monitors"] = []

        state_msg = {
            "version": 1,
            "type": "lighting_state",
            "payload": {
                "mode": self.app_state.mode,
                "output_mode": self.app_state.output_mode,
                "power_on": self.app_state.power_on,
                "color": {
                    "r": self.engine.priority_manager.base_state.r,
                    "g": self.engine.priority_manager.base_state.g,
                    "b": self.engine.priority_manager.base_state.b
                },
                "brightness": self.engine.user_brightness, # Target brightness
                "device": {
                    "connected": connected,
                    "transport": active_transport
                },
                "analyzers": self.analyzer_manager.get_status(),
                "music_settings": self.app_state.settings.get("music", {}),
                "music_mappings": self.app_state.get_music_mappings(),
                "response_mode": self.app_state.get_music_response_mode(),
                "movie_settings": movie_settings,
                "movie_layout": self.app_state.get_movie_layout().to_dict() if hasattr(self.app_state, "get_movie_layout") else {},
                "custom_effect": self.app_state.get_custom_effect() if hasattr(self.app_state, "get_custom_effect") else "rainfall",
                "custom_config": self.app_state.get_custom_config() if hasattr(self.app_state, "get_custom_config") else {},
                "custom_settings": self.app_state.get_custom_settings() if hasattr(self.app_state, "get_custom_settings") else {},
                "developer_state": (
                    self.engine.developer_event_manager.get_state().value
                    if hasattr(self.engine, "developer_event_manager") else "IDLE"
                ),
                "developer_event": (
                    self.engine.developer_event_manager.get_active_event().event_type.value
                    if hasattr(self.engine, "developer_event_manager") and self.engine.developer_event_manager.get_active_event() else None
                ),
                "developer_event_timestamp": (
                    self.engine.developer_event_manager.get_active_event().timestamp
                    if hasattr(self.engine, "developer_event_manager") and self.engine.developer_event_manager.get_active_event() else None
                ),
                "developer_zone_configuration": (
                    self.app_state.get_developer_zones() if hasattr(self.app_state, "get_developer_zones") else {}
                ),
                "developer_zones": (
                    self.app_state.get_developer_zones() if hasattr(self.app_state, "get_developer_zones") else {}
                ),
                "developer_settings": (
                    self.app_state.get_developer_settings() if hasattr(self.app_state, "get_developer_settings") else {}
                ),
                "led_frame": self._get_led_frame_sample(),
                "led_count": getattr(self.app_state, "led_count", 300),
                "audio_telemetry": getattr(self.engine, "latest_music_analysis", None).to_dict() if getattr(self.engine, "latest_music_analysis", None) else {}
            }
        }
        
        msg_str = json.dumps(state_msg)
        websockets.broadcast(self.clients, msg_str)

    async def _handle_command(self, websocket, message):
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            payload = data.get("payload", {})

            if msg_type == "ping":
                await websocket.send(json.dumps({"version": 1, "type": "pong", "payload": {}}))
                
            elif msg_type == "get_state":
                await self.broadcast_state()

            elif msg_type == "set_mode":
                mode = payload.get("mode")
                if mode:
                    settings = self.app_state.set_mode(mode)
                    if settings and mode == "custom":
                        self.engine.set_ambient_color(settings.get("r", 255), settings.get("g", 255), settings.get("b", 255))
                        if hasattr(self.engine, "custom_effect_engine"):
                            eff = self.app_state.get_custom_effect()
                            cfg = self.app_state.get_custom_config(eff)
                            self.engine.custom_effect_engine.set_effect(eff, cfg)
                            self.engine.custom_start_time = time.time()
                    logger.info(f"Mode set to {mode}")
                    self.analyzer_manager.check_state()
                    await self.broadcast_state()
                    
            elif msg_type == "set_power":
                power = payload.get("power_on")
                if power is not None:
                    self.app_state.set_power(power)
                    logger.info(f"Power set to {power}")
                    await self.broadcast_state()

            elif msg_type == "set_output_mode":
                output_mode = payload.get("output_mode")
                if output_mode:
                    self.app_state.set_output_mode(output_mode)
                    logger.info(f"Output mode set to {output_mode}")
                    await self.broadcast_state()

            elif msg_type == "set_color":
                r = payload.get("r", 0)
                g = payload.get("g", 0)
                b = payload.get("b", 0)
                self.engine.set_ambient_color(r, g, b)
                if hasattr(self.app_state, "get_custom_effect") and hasattr(self.app_state, "set_custom_config"):
                    eff = self.app_state.get_custom_effect()
                    self.app_state.set_custom_config(eff, {"color": {"r": r, "g": g, "b": b}})
                    if hasattr(self.engine, "custom_effect_engine"):
                        self.engine.custom_effect_engine.update_config(eff, {"color": {"r": r, "g": g, "b": b}})
                logger.info(f"Color set to {r}, {g}, {b}")
                await self.broadcast_state()

            elif msg_type == "set_music_colors":
                bass = payload.get("bass_color")
                mid = payload.get("mid_color")
                treb = payload.get("treb_color")
                self.app_state.update_music_colors(bass, mid, treb)
                logger.info("Music colors updated")
                await self.broadcast_state()

            elif msg_type == "get_music_mappings":
                resp = {
                    "version": 1,
                    "type": "music_mappings",
                    "payload": {
                        "mappings": self.app_state.get_music_mappings(),
                        "led_count": getattr(self.app_state, "led_count", 300)
                    }
                }
                await websocket.send(json.dumps(resp))

            elif msg_type == "set_music_mappings":
                mappings = payload.get("mappings", [])
                ok, err = self.app_state.set_music_mappings(mappings)
                if not ok:
                    await self._send_error(websocket, "VALIDATION_ERROR", err or "Invalid mappings")
                else:
                    logger.info("Music mappings updated successfully")
                    await self.broadcast_state()

            elif msg_type == "set_music_mapping":
                mapping = payload.get("mapping", {})
                ok, err = self.app_state.set_music_mapping(mapping)
                if not ok:
                    await self._send_error(websocket, "VALIDATION_ERROR", err or "Invalid mapping")
                else:
                    logger.info("Music mapping updated")
                    await self.broadcast_state()

            elif msg_type == "delete_music_mapping":
                mapping_id = payload.get("id")
                if mapping_id:
                    self.app_state.delete_music_mapping(mapping_id)
                    logger.info(f"Music mapping {mapping_id} deleted")
                    await self.broadcast_state()

            elif msg_type == "apply_music_preset":
                preset = payload.get("preset", "")
                if self.app_state.apply_music_preset(preset):
                    logger.info(f"Music preset '{preset}' applied")
                    await self.broadcast_state()
                else:
                    await self._send_error(websocket, "INVALID_PRESET", f"Unknown preset '{preset}'")

            elif msg_type == "set_music_response_mode":
                mode = payload.get("response_mode") or payload.get("responseMode") or payload.get("mode")
                if mode:
                    mode = str(mode).lower()
                    if mode in ["fade", "flash"]:
                        self.app_state.set_music_response_mode(mode)
                        logger.info(f"Music response mode set to {mode}")
                        await self.broadcast_state()
                    else:
                        await self._send_error(websocket, "INVALID_RESPONSE_MODE", f"Invalid response mode '{mode}'. Must be 'fade' or 'flash'")
                else:
                    await self._send_error(websocket, "MISSING_PARAM", "Missing response_mode in payload")

            elif msg_type == "set_movie_layout":
                layout_data = payload.get("layout", payload)
                ok, err = self.app_state.set_movie_layout(layout_data)
                if not ok:
                    await self._send_error(websocket, "VALIDATION_ERROR", err or "Invalid movie layout")
                else:
                    logger.info("Movie layout updated")
                    await self.broadcast_state()

            elif msg_type == "set_movie_music_sync":
                sync = payload.get("sync_music", payload.get("enabled", False))
                self.app_state.set_movie_music_sync(bool(sync))
                logger.info(f"Movie music sync set to {sync}")
                self.analyzer_manager.check_state()
                await self.broadcast_state()

            elif msg_type == "set_movie_settings":
                ok, err = self.app_state.set_movie_settings(payload)
                if not ok:
                    await self._send_error(websocket, "VALIDATION_ERROR", err or "Invalid movie settings")
                else:
                    logger.info("Movie settings updated")
                    self.analyzer_manager.check_state()
                    await self.broadcast_state()

            elif msg_type == "get_monitors":
                try:
                    from analyzers.screen_analyzer import ScreenAnalyzer
                    monitors = ScreenAnalyzer.get_available_monitors()
                except Exception:
                    monitors = []
                resp = {
                    "version": 1,
                    "type": "available_monitors",
                    "payload": {"monitors": monitors}
                }
                await websocket.send(json.dumps(resp))

            elif msg_type == "set_movie_monitor":
                idx = int(payload.get("monitor_index", payload.get("id", 1)))
                if hasattr(self.app_state, "set_movie_monitor"):
                    self.app_state.set_movie_monitor(idx)
                else:
                    self.app_state.settings.setdefault("movie", {})["monitor_index"] = idx
                    self.app_state.save()
                logger.info(f"Movie monitor set to {idx}")
                await self.broadcast_state()

            elif msg_type == "get_custom_effect":
                resp = {
                    "version": 1,
                    "type": "custom_effect",
                    "payload": {
                        "effect": self.app_state.get_custom_effect() if hasattr(self.app_state, "get_custom_effect") else "rainfall",
                        "config": self.app_state.get_custom_config() if hasattr(self.app_state, "get_custom_config") else {},
                        "settings": self.app_state.get_custom_settings() if hasattr(self.app_state, "get_custom_settings") else {}
                    }
                }
                await websocket.send(json.dumps(resp))

            elif msg_type == "set_custom_effect":
                effect = payload.get("effect")
                if effect:
                    ok = self.app_state.set_custom_effect(effect) if hasattr(self.app_state, "set_custom_effect") else False
                    if ok:
                        if hasattr(self.engine, "custom_effect_engine"):
                            cfg = self.app_state.get_custom_config(effect)
                            self.engine.custom_effect_engine.set_effect(effect, cfg)
                            self.engine.custom_start_time = time.time()
                        logger.info(f"Custom effect set to {effect}")
                        await self.broadcast_state()
                    else:
                        await self._send_error(websocket, "INVALID_EFFECT", f"Unknown custom effect: {effect}")
                else:
                    await self._send_error(websocket, "MISSING_PARAM", "Missing effect name in payload")

            elif msg_type == "set_custom_config":
                effect = payload.get("effect") or (self.app_state.get_custom_effect() if hasattr(self.app_state, "get_custom_effect") else None)
                config = payload.get("config", {})
                if effect and isinstance(config, dict):
                    ok, err = self.app_state.set_custom_config(effect, config) if hasattr(self.app_state, "set_custom_config") else (False, "Method not supported")
                    if ok:
                        if hasattr(self.engine, "custom_effect_engine"):
                            self.engine.custom_effect_engine.update_config(effect, config)
                        logger.info(f"Custom config updated for {effect}")
                        await self.broadcast_state()
                    else:
                        await self._send_error(websocket, "VALIDATION_ERROR", err or "Failed to update custom config")
                else:
                    await self._send_error(websocket, "INVALID_PARAM", "Invalid effect or config dictionary")

            elif msg_type == "set_brightness":
                # Expects 0.0 to 1.0
                val = payload.get("value", 1.0)
                self.engine.set_user_brightness(val)
                logger.info(f"Brightness set to {val}")
                await self.broadcast_state()

            elif msg_type == "trigger_event":
                r = payload.get("r", 255)
                g = payload.get("g", 255)
                b = payload.get("b", 255)
                duration = payload.get("duration", 1.0)
                priority = payload.get("priority", EventPriority.LOW.value)
                self.engine.trigger_event(r, g, b, duration, EventPriority(priority))

            elif msg_type == "trigger_developer_event":
                event_name = payload.get("event") or payload.get("event_type")
                priority = payload.get("priority")
                duration = payload.get("duration")
                metadata = payload.get("metadata", {})
                if hasattr(self.engine, "trigger_developer_event"):
                    ok, err, res = self.engine.trigger_developer_event(event_name, priority, duration, metadata)
                    if ok:
                        await self.broadcast_state()
                    else:
                        await self._send_error(websocket, "INVALID_EVENT", err or "Failed to trigger event")
                else:
                    await self._send_error(websocket, "NOT_SUPPORTED", "Developer mode not supported by engine")

            elif msg_type == "set_developer_zones":
                zones_data = payload.get("zones", payload)
                if hasattr(self.app_state, "set_developer_zones"):
                    ok, err = self.app_state.set_developer_zones(zones_data)
                    if not ok:
                        await self._send_error(websocket, "VALIDATION_ERROR", err or "Invalid developer zones")
                    else:
                        await self.broadcast_state()

            elif msg_type == "set_developer_settings":
                settings_data = payload.get("settings", payload)
                if hasattr(self.app_state, "set_developer_settings"):
                    ok, err = self.app_state.set_developer_settings(settings_data)
                    if not ok:
                        await self._send_error(websocket, "VALIDATION_ERROR", err or "Invalid developer settings")
                    else:
                        await self.broadcast_state()

            elif msg_type == "restart_all":
                logger.info("Restart All requested by user / UI")
                ok = False
                if hasattr(self.engine.transport, 'hard_reset_hardware'):
                    ok = self.engine.transport.hard_reset_hardware()
                elif hasattr(self.engine.transport, 'serial_transport'):
                    ok = self.engine.transport.serial_transport.hard_reset_hardware()

                if hasattr(self.engine, 'reset_state'):
                    self.engine.reset_state()

                if self.analyzer_manager:
                    self.analyzer_manager.check_state()

                logger.info(f"Restart All finished (hardware reset: {ok})")
                await websocket.send(json.dumps({
                    "version": 1,
                    "type": "restart_complete",
                    "payload": {
                        "status": "success" if ok else "warning",
                        "message": "Hardware and engine successfully restarted"
                    }
                }))
                await self.broadcast_state()

            else:
                await self._send_error(websocket, "INVALID_MESSAGE", f"Unknown command type: {msg_type}")

        except json.JSONDecodeError:
            await self._send_error(websocket, "INVALID_MESSAGE", "Invalid JSON payload")
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            await self._send_error(websocket, "ENGINE_ERROR", str(e))

    async def _send_error(self, websocket, code, message):
        error_msg = {
            "version": 1,
            "type": "error",
            "payload": {
                "code": code,
                "message": message
            }
        }
        await websocket.send(json.dumps(error_msg))

    async def _handler(self, websocket):
        self.clients.add(websocket)
        logger.info("Client connected")
        await self.broadcast_state()
        try:
            async for message in websocket:
                await self._handle_command(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            logger.info("Client disconnected")

    async def start_server(self):
        self._loop = asyncio.get_running_loop()
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        # Start the background broadcast loop
        asyncio.create_task(self._broadcast_loop())
        
        async with websockets.serve(self._handler, self.host, self.port):
            await asyncio.Future()  # run forever

    async def _broadcast_loop(self):
        # Broadcast the render_state at 20Hz so the Virtual Strip is smooth
        while True:
            await asyncio.sleep(0.05) # 20 FPS
            if self.clients:
                # Use the SMOOTHED render state, not the base_state
                state = self.engine.render_state
                
                if hasattr(self.engine.transport, 'get_active_transport_name'):
                    active_transport = self.engine.transport.get_active_transport_name()
                    connected = self.engine.transport.serial_transport.is_connected()
                else:
                    active_transport = self.engine.transport.__class__.__name__ if self.engine.transport else "none"
                    connected = self.engine.transport.is_connected() if self.engine.transport else False

                state_msg = {
                    "version": 1,
                    "type": "lighting_state",
                    "payload": {
                        "mode": self.app_state.mode,
                        "output_mode": self.app_state.output_mode,
                        "power_on": self.app_state.power_on,
                        "color": {
                            "r": state.r,
                            "g": state.g,
                            "b": state.b
                        },
                        "brightness": self.engine.user_brightness, # The slider target
                        "render_brightness": state.brightness / 255.0, # The smoothed output
                        "device": {
                            "connected": connected,
                            "transport": active_transport
                        },
                        "analyzers": self.analyzer_manager.get_status(),
                        "music_settings": self.app_state.settings.get("music", {}),
                        "music_mappings": self.app_state.get_music_mappings(),
                        "response_mode": self.app_state.get_music_response_mode(),
                        "movie_settings": self.app_state.get_movie_settings() if hasattr(self.app_state, "get_movie_settings") else {},
                        "movie_layout": self.app_state.get_movie_layout().to_dict() if hasattr(self.app_state, "get_movie_layout") else {},
                        "custom_effect": self.app_state.get_custom_effect() if hasattr(self.app_state, "get_custom_effect") else "rainfall",
                        "custom_config": self.app_state.get_custom_config() if hasattr(self.app_state, "get_custom_config") else {},
                        "custom_settings": self.app_state.get_custom_settings() if hasattr(self.app_state, "get_custom_settings") else {},
                        "led_frame": self._get_led_frame_sample(),
                        "led_count": getattr(self.app_state, "led_count", 300),
                        "audio_telemetry": getattr(self.engine, "latest_music_analysis", None).to_dict() if getattr(self.engine, "latest_music_analysis", None) else {}
                    }
                }
                websockets.broadcast(self.clients, json.dumps(state_msg))
