export type LightingMode =
  | 'movie'
  | 'music'
  | 'game'
  | 'developer'
  | 'custom';

export interface RGBColor {
  r: number;
  g: number;
  b: number;
}

export type TransportType = 'usb' | 'wifi' | 'none';

export type OutputMode = 'auto' | 'virtual' | 'esp32';

export interface LightingState {
  mode: LightingMode;
  outputMode: OutputMode;
  color: RGBColor;
  brightness: number; // The user-facing target
  renderBrightness?: number; // The smoothed output for visuals
  connected: boolean;
  transport: TransportType;
  analyzers?: {
    screen_analyzer?: string;
  };
}

// Mode Specific Settings
export interface MovieModeSettings {
  screenSync: boolean;
  audioBrightness: boolean;
  maxBrightness: number;
  smoothing: 'Low' | 'Medium' | 'High';
}

export interface MusicModeSettings {
  bassSensitivity: number;
  midSensitivity: number;
  highSensitivity: number;
  maxBrightness: number;
}

export interface GameModeSettings {
  screenSync: boolean;
  audioBrightness: boolean;
  maxBrightness: number;
  response: 'Low' | 'Medium' | 'High';
}

export interface DeveloperModeSettings {
  buildFailureEffect: 'Pulse' | 'Static' | 'Flash';
  buildSuccessEffect: 'Pulse' | 'Static' | 'Flash';
  eventDuration: number; // seconds
}

export interface CustomModeSettings {
  color: RGBColor;
  brightness: number;
  effect: 'Static' | 'Pulse' | 'Breathing';
}
