import type { ILightingService } from './LightingService';
import type { LightingMode, RGBColor, LightingState, MusicResponseMode, CustomEffectType, CustomEffectConfig } from '../types/lighting';

export class RealLightingService implements ILightingService {
  private ws: WebSocket | null = null;
  private url = 'ws://127.0.0.1:8765';
  
  private stateCallbacks: ((state: LightingState) => void)[] = [];
  private connectionCallbacks: ((connected: boolean) => void)[] = [];
  
  private reconnectTimer: any = null;
  private backoff = 1000;
  private maxBackoff = 5000;
  private commandQueue: Map<string, any> = new Map();
  private pingTimer: any = null;
  private pongTimeout: any = null;


  async connect(): Promise<void> {
    if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    console.log('[LightingService] Connecting to Engine...', this.url);
    
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
          console.log('[LightingService] Connected to Engine');
          this.backoff = 1000; // reset
          this.notifyConnection(true);
          
          this.startHeartbeat();
          
          // Request initial state
          this.getState().catch(console.error);
          
          // Flush queue
          this.commandQueue.forEach((payload, type) => {
             this.sendCommand(type, payload, true);
          });
          this.commandQueue.clear();
          
          resolve();
        };

        this.ws.onclose = () => {
          console.log('[LightingService] Disconnected from Engine');
          this.stopHeartbeat();
          this.notifyConnection(false);
          this.ws = null;
          this.scheduleReconnect();
        };

        this.ws.onerror = (err) => {
          console.error('[LightingService] WebSocket Error:', err);
          // onclose will handle the reconnect
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (e) {
            console.error('[LightingService] Failed to parse message', e);
          }
        };

      } catch (e) {
        console.error('[LightingService] Failed to create WebSocket', e);
        this.scheduleReconnect();
        reject(e);
      }
    });
  }

  disconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    
    console.log(`[LightingService] Reconnecting in ${this.backoff}ms...`);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.backoff = Math.min(this.backoff * 1.5, this.maxBackoff);
      this.connect().catch(() => {});
    }, this.backoff);
  }

  private handleMessage(data: any) {
    if (data.version !== 1) return;

    if (data.type === 'pong') {
      if (this.pongTimeout) {
        clearTimeout(this.pongTimeout);
        this.pongTimeout = null;
      }
      return;
    }

    if (data.type === 'lighting_state') {
      const p = data.payload;
      const rawMappings = p.music_mappings || [];
      const musicMappings = rawMappings.map((m: any) => ({
        id: m.id,
        instrument: m.instrument,
        color: m.color,
        startLed: m.start_led,
        endLed: m.end_led,
        sensitivity: m.sensitivity,
        response: m.response,
        distribution: m.distribution,
        enabled: m.enabled,
        seed: m.seed ?? 42
      }));

      const mappedState: LightingState = {
        mode: p.mode,
        outputMode: p.output_mode || 'auto',
        power_on: p.power_on ?? true,
        color: p.color, // { r, g, b }
        brightness: p.brightness * 100, // Target brightness
        renderBrightness: (p.render_brightness ?? p.brightness) * 100, // Smoothed brightness
        connected: p.device.connected,
        transport: p.device.transport === 'serial' ? 'usb' : 'none',
        analyzers: p.analyzers,
        musicSettings: p.music_settings,
        musicResponseMode: (p.response_mode || p.music_settings?.response_mode || 'flash') as any,
        musicMappings,
        movieSettings: p.movie_settings,
        movieLayout: p.movie_layout,
        customEffect: p.custom_effect,
        customConfig: p.custom_config,
        customSettings: p.custom_settings,
        ledFrame: p.led_frame,
        ledCount: p.led_count ?? 300,
        virtualFrame: p.virtual_frame
      };
      
      this.stateCallbacks.forEach(cb => cb(mappedState));
    }
    else if (data.type === 'error') {
      console.error('[LightingService] Engine Error:', data.payload.code, data.payload.message);
    }
  }

  private sendCommand(type: string, payload: any = {}, ignoreQueue = false): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      if (!ignoreQueue) {
        console.warn(`[LightingService] Cannot send ${type}, queuing until connected.`);
        this.commandQueue.set(type, payload);
      }
      return;
    }
    
    const msg = {
      version: 1,
      type,
      payload
    };
    
    this.ws.send(JSON.stringify(msg));
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.pingTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.sendCommand('ping', {}, true);
        this.pongTimeout = setTimeout(() => {
          console.warn('[LightingService] Engine missed pong. Forcing reconnect.');
          if (this.ws) this.ws.close();
        }, 5000); // 5 sec to reply
      }
    }, 15000); // Ping every 15s
  }

  private stopHeartbeat() {
    if (this.pingTimer) clearInterval(this.pingTimer);
    if (this.pongTimeout) clearTimeout(this.pongTimeout);
    this.pingTimer = null;
    this.pongTimeout = null;
  }

  async getState(): Promise<LightingState> {
    this.sendCommand('get_state');
    return {} as LightingState;
  }

  async ping(): Promise<boolean> {
    this.sendCommand('ping');
    return true;
  }

  async setMode(mode: LightingMode): Promise<void> {
    this.sendCommand('set_mode', { mode });
  }

  async setPower(isOn: boolean): Promise<void> {
    this.sendCommand('set_power', { power_on: isOn });
  }

  async setOutputMode(outputMode: string): Promise<void> {
    this.sendCommand('set_output_mode', { output_mode: outputMode });
  }

  async setBrightness(value: number): Promise<void> {
    this.sendCommand('set_brightness', { value: value / 100.0 });
  }

  async setMusicColors(bass?: RGBColor, mid?: RGBColor, treb?: RGBColor): Promise<void> {
    this.sendCommand("set_music_colors", { bass_color: bass, mid_color: mid, treb_color: treb });
  }

  async setMusicMappings(mappings: any[]): Promise<void> {
    const serialized = mappings.map((m: any) => ({
      id: m.id,
      instrument: m.instrument,
      color: m.color,
      start_led: m.startLed ?? m.start_led,
      end_led: m.endLed ?? m.end_led,
      sensitivity: m.sensitivity,
      response: m.response,
      distribution: m.distribution,
      enabled: m.enabled,
      seed: m.seed ?? 42
    }));
    this.sendCommand('set_music_mappings', { mappings: serialized });
  }

  async setMusicMapping(mapping: any): Promise<void> {
    const serialized = {
      id: mapping.id,
      instrument: mapping.instrument,
      color: mapping.color,
      start_led: mapping.startLed ?? mapping.start_led,
      end_led: mapping.endLed ?? mapping.end_led,
      sensitivity: mapping.sensitivity,
      response: mapping.response,
      distribution: mapping.distribution,
      enabled: mapping.enabled,
      seed: mapping.seed ?? 42
    };
    this.sendCommand('set_music_mapping', { mapping: serialized });
  }

  async deleteMusicMapping(id: string): Promise<void> {
    this.sendCommand('delete_music_mapping', { id });
  }

  async applyMusicPreset(presetName: string): Promise<void> {
    this.sendCommand('apply_music_preset', { preset: presetName });
  }

  async setMusicResponseMode(mode: MusicResponseMode): Promise<void> {
    this.sendCommand('set_music_response_mode', { response_mode: mode });
  }

  async setMovieLayout(layout: any): Promise<void> {
    this.sendCommand('set_movie_layout', { layout });
  }

  async setMovieMusicSync(enabled: boolean): Promise<void> {
    this.sendCommand('set_movie_music_sync', { sync_music: enabled });
  }

  async setMovieSettings(settings: any): Promise<void> {
    this.sendCommand('set_movie_settings', settings);
  }

  async setMovieMonitor(monitorIndex: number): Promise<void> {
    this.sendCommand('set_movie_monitor', { monitor_index: monitorIndex });
  }

  async setCustomEffect(effect: CustomEffectType): Promise<void> {
    this.sendCommand('set_custom_effect', { effect });
  }

  async setCustomEffectConfig(effect: CustomEffectType, config: CustomEffectConfig): Promise<void> {
    this.sendCommand('set_custom_config', { effect, config });
  }

  async triggerDeveloperEvent(event: string, priority?: number, duration?: number): Promise<void> {
    this.sendCommand('trigger_developer_event', { event, priority, duration });
  }

  async restartAll(): Promise<boolean> {
    this.sendCommand('restart_all', {});
    return true;
  }

  async setColor(color: RGBColor): Promise<void> {
    this.sendCommand('set_color', color);
  }

  onStateChange(callback: (state: LightingState) => void): void {
    this.stateCallbacks.push(callback);
  }

  onConnectionChange(callback: (connected: boolean) => void): void {
    this.connectionCallbacks.push(callback);
  }
  
  private notifyConnection(connected: boolean) {
    this.connectionCallbacks.forEach(cb => cb(connected));
  }
}
