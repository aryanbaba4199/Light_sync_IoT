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

export const DEFAULT_LED_COUNT = 300;

export type MusicInstrument =
  | 'bass'
  | 'kick'
  | 'snare'
  | 'vocal'
  | 'hihat'
  | 'brass'
  | 'melody'
  | 'beat'
  | 'overall';

export type MusicResponseEffect = 'static' | 'pulse' | 'flash' | 'smooth';

export type MusicResponseMode = 'fade' | 'flash';

export type MusicDistribution = 'zone' | 'random';

export interface MusicMapping {
  id: string;
  instrument: MusicInstrument;
  color: RGBColor;
  startLed: number; // 1-based (1 to DEFAULT_LED_COUNT)
  endLed: number;   // 1-based (1 to DEFAULT_LED_COUNT)
  sensitivity: number; // 0.0 to 2.0 (e.g. 1.0 = 100%)
  response: MusicResponseEffect;
  distribution: MusicDistribution;
  enabled: boolean;
  seed: number;
}

export interface MovieLayout {
  top: number;
  right: number;
  bottom: number;
  left: number;
  sampling_thickness?: number;
  clockwise?: boolean;
  total_leds?: number;
}

export interface MovieSettings {
  top?: number;
  right?: number;
  bottom?: number;
  left?: number;
  sampling_thickness?: number;
  clockwise?: boolean;
  sync_music?: boolean;
  smoothing?: number;
  brightness_limit?: number;
  min_music_brightness?: number;
  max_music_brightness?: number;
}

export interface LightingState {
  mode: LightingMode;
  outputMode: OutputMode;
  power_on: boolean;
  color: RGBColor;
  musicSettings?: any;
  musicResponseMode?: MusicResponseMode;
  musicMappings?: MusicMapping[];
  movieSettings?: MovieSettings;
  movieLayout?: MovieLayout;
  ledCount?: number;
  virtualFrame?: RGBColor[];
  brightness: number; // The user-facing target
  renderBrightness?: number; // The smoothed output for visuals
  connected: boolean;
  transport: TransportType;
  analyzers?: {
    screen_analyzer?: string;
    music_analyzer?: string;
  };
  audioTelemetry?: {
    bass?: number;
    kick?: number;
    snare?: number;
    vocal?: number;
    hihat?: number;
    brass?: number;
    melody?: number;
    beat?: number;
    overall?: number;
    kick_trigger?: boolean;
    snare_trigger?: boolean;
    hihat_trigger?: boolean;
    music_gate_open?: boolean;
    bass_transient?: number;
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
  musicSettings?: any;
  brightness: number;
  effect: 'Static' | 'Pulse' | 'Breathing';
}
