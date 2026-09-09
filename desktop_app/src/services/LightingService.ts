import type { LightingMode, RGBColor, LightingState } from '../types/lighting';

export interface ILightingService {
  connect(): Promise<void>;
  disconnect(): void;
  
  // Queries
  getState(): Promise<LightingState>;
  ping(): Promise<boolean>;

  // Commands
  setMode(mode: LightingMode): Promise<void>;
  setOutputMode(outputMode: string): Promise<void>;
  setBrightness(value: number): Promise<void>; // 0 to 100
  setColor(color: RGBColor): Promise<void>;
  
  // Callbacks
  onStateChange(callback: (state: LightingState) => void): void;
  onConnectionChange(callback: (connected: boolean) => void): void;
}
