import type { LightingMode, RGBColor, LightingState, MusicResponseMode, CustomEffectType, CustomEffectConfig } from '../types/lighting';

export interface ILightingService {
  connect(): Promise<void>;
  disconnect(): void;
  
  // Queries
  getState(): Promise<LightingState>;
  ping(): Promise<boolean>;

  // Commands
  setMode(mode: LightingMode): Promise<void>;
  setPower(isOn: boolean): Promise<void>;
  setOutputMode(outputMode: string): Promise<void>;
  setBrightness(value: number): Promise<void>; // 0 to 100
  setColor(color: RGBColor): Promise<void>;
  setCustomEffect(effect: CustomEffectType): Promise<void>;
  setCustomEffectConfig(effect: CustomEffectType, config: CustomEffectConfig): Promise<void>;
  setMusicColors(bass?: RGBColor, mid?: RGBColor, treb?: RGBColor): Promise<void>;
  setMusicMappings(mappings: any[]): Promise<void>;
  setMusicMapping(mapping: any): Promise<void>;
  deleteMusicMapping(id: string): Promise<void>;
  applyMusicPreset(presetName: string): Promise<void>;
  setMusicResponseMode(mode: MusicResponseMode): Promise<void>;
  setMovieLayout(layout: any): Promise<void>;
  setMovieMusicSync(enabled: boolean): Promise<void>;
  setMovieSettings(settings: any): Promise<void>;
  setMovieMonitor(monitorIndex: number): Promise<void>;
  restartAll(): Promise<boolean>;

  
  // Callbacks
  onStateChange(callback: (state: LightingState) => void): void;
  onConnectionChange(callback: (connected: boolean) => void): void;
}
