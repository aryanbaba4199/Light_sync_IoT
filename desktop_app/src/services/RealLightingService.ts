import type { ILightingService } from './LightingService';
import type { LightingMode, RGBColor, LightingState } from '../types/lighting';

export class RealLightingService implements ILightingService {
  private ws: WebSocket | null = null;
  private url = 'ws://127.0.0.1:8765';
  
  private stateCallbacks: ((state: LightingState) => void)[] = [];
  private connectionCallbacks: ((connected: boolean) => void)[] = [];
  
  private reconnectTimer: any = null;
  private backoff = 1000;
  private maxBackoff = 5000;

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
          
          // Request initial state
          this.getState().catch(console.error);
          resolve();
        };

        this.ws.onclose = () => {
          console.log('[LightingService] Disconnected from Engine');
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

    if (data.type === 'lighting_state') {
      const p = data.payload;
      const mappedState: LightingState = {
        mode: p.mode,
        outputMode: p.output_mode || 'auto',
        power_on: p.power_on ?? true,
        color: p.color, // { r, g, b }
        brightness: p.brightness * 100, // Target brightness
        renderBrightness: (p.render_brightness ?? p.brightness) * 100, // Smoothed brightness
        connected: p.device.connected,
        transport: p.device.transport === 'serial' ? 'usb' : 'none',
        analyzers: p.analyzers
      };
      
      this.stateCallbacks.forEach(cb => cb(mappedState));
    }
    else if (data.type === 'error') {
      console.error('[LightingService] Engine Error:', data.payload.code, data.payload.message);
    }
  }

  private sendCommand(type: string, payload: any = {}): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn(`[LightingService] Cannot send ${type}, engine disconnected.`);
      return;
    }
    
    const msg = {
      version: 1,
      type,
      payload
    };
    
    this.ws.send(JSON.stringify(msg));
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
