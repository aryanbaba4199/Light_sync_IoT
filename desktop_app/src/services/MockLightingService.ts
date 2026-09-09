import type { ILightingService } from './LightingService';
import type { LightingMode, RGBColor, LightingState } from '../types/lighting';

export class MockLightingService implements ILightingService {
  private state: LightingState = {
    mode: 'movie',
    color: { r: 139, g: 92, b: 246 },
    brightness: 74,
    connected: true,
    transport: 'none'
  };

  private stateCallbacks: ((state: LightingState) => void)[] = [];
  private connectionCallbacks: ((connected: boolean) => void)[] = [];

  async connect(): Promise<void> {
    console.log('[MockService] Connected');
    setTimeout(() => {
      this.connectionCallbacks.forEach(cb => cb(true));
      this.notifyState();
    }, 500);
  }

  disconnect(): void {
    console.log('[MockService] Disconnected');
    this.connectionCallbacks.forEach(cb => cb(false));
  }

  async getState(): Promise<LightingState> {
    return this.state;
  }

  async ping(): Promise<boolean> {
    return true;
  }

  async setOutputMode(mode: string): Promise<void> {}

  async setMode(mode: LightingMode): Promise<void> {
    this.state.mode = mode;
    this.notifyState();
  }

  async setBrightness(value: number): Promise<void> {
    this.state.brightness = value;
    this.notifyState();
  }

  async setColor(color: RGBColor): Promise<void> {
    this.state.color = color;
    this.notifyState();
  }

  onStateChange(callback: (state: LightingState) => void): void {
    this.stateCallbacks.push(callback);
  }

  onConnectionChange(callback: (connected: boolean) => void): void {
    this.connectionCallbacks.push(callback);
  }

  private notifyState() {
    this.stateCallbacks.forEach(cb => cb(this.state));
  }
}
