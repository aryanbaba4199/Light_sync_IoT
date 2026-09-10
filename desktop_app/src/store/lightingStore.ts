import { create } from 'zustand';
import type { 
  LightingMode, 
  RGBColor, 
  TransportType, 
  OutputMode, 
  MusicMapping, 
  MusicInstrument, 
  MusicResponseMode, 
  MovieLayout, 
  MovieSettings,
  CustomEffectType,
  CustomEffectConfig,
  CustomSettings
} from '../types/lighting';
import { DEFAULT_LED_COUNT } from '../types/lighting';
import { lightingService } from '../services';

export const INSTRUMENT_COLORS: Record<MusicInstrument, RGBColor> = {
  bass: { r: 255, g: 0, b: 0 },
  kick: { r: 255, g: 100, b: 0 },
  snare: { r: 255, g: 210, b: 0 },
  vocal: { r: 180, g: 0, b: 255 },
  hihat: { r: 0, g: 200, b: 255 },
  brass: { r: 255, g: 150, b: 30 },
  melody: { r: 0, g: 255, b: 100 },
  beat: { r: 255, g: 255, b: 255 },
  overall: { r: 255, g: 0, b: 150 }
};

export const checkOverlaps = (mappings: MusicMapping[]): string[] => {
  const warnings: string[] = [];
  const enabled = mappings.filter(m => m.enabled);
  for (let i = 0; i < enabled.length; i++) {
    for (let j = i + 1; j < enabled.length; j++) {
      const m1 = enabled[i];
      const m2 = enabled[j];
      if (!(m1.endLed < m2.startLed || m1.startLed > m2.endLed)) {
        warnings.push(
          `${m1.instrument.toUpperCase()} (LED ${m1.startLed}–${m1.endLed}) overlaps with ${m2.instrument.toUpperCase()} (LED ${m2.startLed}–${m2.endLed})`
        );
      }
    }
  }
  return warnings;
};

interface LightingStore {
  mode: LightingMode;
  outputMode: OutputMode;
  power_on: boolean;
  color: RGBColor;
  brightness: number;
  renderBrightness: number;
  connected: boolean;
  transport: TransportType;
  engineConnected: boolean;
  musicSettings: any;
  musicResponseMode: MusicResponseMode;
  musicMappings: MusicMapping[];
  movieLayout: MovieLayout;
  movieSettings: MovieSettings;
  customEffect: CustomEffectType;
  customConfig: CustomEffectConfig;
  customSettings?: CustomSettings;
  developerState: 'IDLE' | 'CODING' | 'BUILDING' | 'TESTING' | 'DEPLOYING';
  developerEvent: string | null;
  developerEventTimestamp: number | null;
  developerZones: Record<string, any>;
  developerSettings: Record<string, any>;
  ledFrame?: [number, number, number][];
  ledCount: number;
  validationWarnings: string[];
  setMusicColors: (bass?: RGBColor, mid?: RGBColor, treb?: RGBColor) => void;
  analyzers: {
    screen_analyzer?: string;
    music_analyzer?: string;
  };
  audioTelemetry?: any;
  
  // Actions
  setMode: (mode: LightingMode) => void;
  setOutputMode: (mode: OutputMode) => void;
  setPower: (isOn: boolean) => void;
  setColor: (color: RGBColor) => void;
  setBrightness: (brightness: number) => void;
  setCustomEffect: (effect: CustomEffectType) => void;
  setCustomEffectConfig: (effect: CustomEffectType, config: Partial<CustomEffectConfig>) => void;
  triggerDeveloperEvent: (event: string, priority?: number, duration?: number) => void;
  setMusicResponseMode: (mode: MusicResponseMode) => void;
  setMovieLayout: (layout: Partial<MovieLayout>) => void;
  setMovieMusicSync: (enabled: boolean) => void;
  setMovieSamplingThickness: (thickness: number) => void;
  setMovieMonitor: (monitorIndex: number) => void;
  addMusicMapping: (instrument?: MusicInstrument) => void;

  updateMusicMapping: (id: string, updates: Partial<MusicMapping>) => void;
  deleteMusicMapping: (id: string) => void;
  applyMusicPreset: (presetName: 'default_3_band' | 'party' | 'full_band') => void;
  reshuffleMappingSeed: (id: string) => void;
  restartAll: () => Promise<boolean>;
  initialize: () => void;
}

export const useLightingStore = create<LightingStore>((set, get) => ({
  mode: 'custom',
  outputMode: 'auto',
  power_on: true,
  color: { r: 255, g: 0, b: 0 },
  brightness: 100,
  renderBrightness: 100,
  connected: false,
  transport: 'none',
  engineConnected: false,
  musicSettings: { bass_color: {r:255,g:0,b:0}, mid_color: {r:0,g:255,b:0}, treb_color: {r:0,g:0,b:255} },
  musicResponseMode: 'flash',
  musicMappings: [
    { id: '1', instrument: 'bass', color: { r: 255, g: 0, b: 0 }, startLed: 1, endLed: 100, sensitivity: 1.0, response: 'static', distribution: 'zone', enabled: true, seed: 101 },
    { id: '2', instrument: 'vocal', color: { r: 0, g: 255, b: 0 }, startLed: 101, endLed: 200, sensitivity: 1.0, response: 'static', distribution: 'zone', enabled: true, seed: 102 },
    { id: '3', instrument: 'hihat', color: { r: 0, g: 0, b: 255 }, startLed: 201, endLed: 300, sensitivity: 1.0, response: 'static', distribution: 'zone', enabled: true, seed: 103 },
  ],
  movieLayout: {
    top: 100,
    right: 50,
    bottom: 100,
    left: 50,
    sampling_thickness: 0.10,
    clockwise: true,
    total_leds: 300
  },
  movieSettings: {
    sync_music: false,
    smoothing: 0.70,
    brightness_limit: 1.0,
    min_music_brightness: 0.35,
    max_music_brightness: 1.00
  },
  customEffect: 'rainfall',
  customConfig: {
    color: { r: 0, g: 120, b: 255 },
    speed: 50,
    active_led_count: 10,
    trail_length: 10
  },
  developerState: 'IDLE',
  developerEvent: null,
  developerEventTimestamp: null,
  developerZones: {},
  developerSettings: {},
  ledFrame: [],
  ledCount: DEFAULT_LED_COUNT,
  validationWarnings: [],
  analyzers: {},

  setMode: (mode) => {
    lightingService.setMode(mode);
    set({ mode });
  },
  
  setOutputMode: (mode) => {
    lightingService.setOutputMode(mode);
    set({ outputMode: mode });
  },

  setPower: (isOn) => {
    lightingService.setPower(isOn);
    set({ power_on: isOn });
  },

  setMusicColors: (bass, mid, treb) => {
    lightingService.setMusicColors(bass, mid, treb);
  },

  setColor: (color) => {
    lightingService.setColor(color);
    set({ color });
  },
  
  setBrightness: (brightness) => {
    lightingService.setBrightness(brightness);
    set({ brightness });
  },

  setCustomEffect: (effect) => {
    lightingService.setCustomEffect(effect);
    set({ customEffect: effect });
  },

  setCustomEffectConfig: (effect, config) => {
    const updated = { ...get().customConfig, ...config };
    lightingService.setCustomEffectConfig(effect, updated);
    set({ customConfig: updated });
  },

  triggerDeveloperEvent: (event, priority, duration) => {
    lightingService.triggerDeveloperEvent(event, priority, duration);
  },

  setMusicResponseMode: (mode) => {
    lightingService.setMusicResponseMode(mode);
    set({ musicResponseMode: mode });
  },

  setMovieLayout: (updates) => {
    const newLayout = { ...get().movieLayout, ...updates };
    newLayout.total_leds = newLayout.top + newLayout.right + newLayout.bottom + newLayout.left;
    lightingService.setMovieLayout(newLayout);
    set({ movieLayout: newLayout });
  },

  setMovieMusicSync: (enabled) => {
    const newSettings = { ...get().movieSettings, sync_music: enabled };
    lightingService.setMovieMusicSync(enabled);
    set({ movieSettings: newSettings });
  },

  setMovieSamplingThickness: (thickness) => {
    const newLayout = { ...get().movieLayout, sampling_thickness: thickness };
    lightingService.setMovieLayout(newLayout);
    set({ movieLayout: newLayout });
  },

  setMovieMonitor: (monitorIndex) => {
    const newSettings = { ...get().movieSettings, monitor_index: monitorIndex };
    lightingService.setMovieMonitor(monitorIndex);
    set({ movieSettings: newSettings });
  },


  addMusicMapping: (instrument = 'bass') => {
    const mappings = [...get().musicMappings];
    const defaultColor = INSTRUMENT_COLORS[instrument] || { r: 255, g: 0, b: 0 };
    
    // Find next available LED range
    let startLed = 1;
    if (mappings.length > 0) {
      const maxEnd = Math.max(...mappings.map(m => m.endLed));
      if (maxEnd < get().ledCount) {
        startLed = maxEnd + 1;
      }
    }
    const endLed = Math.min(startLed + 39, get().ledCount);

    const newMapping: MusicMapping = {
      id: Math.random().toString(36).substring(2, 9),
      instrument,
      color: defaultColor,
      startLed,
      endLed,
      sensitivity: 1.0,
      response: 'static',
      distribution: 'zone',
      enabled: true,
      seed: Math.floor(Math.random() * 10000)
    };

    const updated = [...mappings, newMapping];
    const warnings = checkOverlaps(updated);
    set({ musicMappings: updated, validationWarnings: warnings });
    lightingService.setMusicMapping(newMapping);
  },

  updateMusicMapping: (id, updates) => {
    const mappings = get().musicMappings.map(m => {
      if (m.id === id) {
        const updated = { ...m, ...updates };
        // Clamp LED bounds to valid range [1, ledCount]
        if (updated.startLed !== undefined) updated.startLed = Math.max(1, Math.min(get().ledCount, updated.startLed));
        if (updated.endLed !== undefined) updated.endLed = Math.max(1, Math.min(get().ledCount, updated.endLed));
        return updated;
      }
      return m;
    });

    const warnings = checkOverlaps(mappings);
    set({ musicMappings: mappings, validationWarnings: warnings });

    const changed = mappings.find(m => m.id === id);
    if (changed) {
      lightingService.setMusicMapping(changed);
    }
  },

  deleteMusicMapping: (id) => {
    const mappings = get().musicMappings.filter(m => m.id !== id);
    const warnings = checkOverlaps(mappings);
    set({ musicMappings: mappings, validationWarnings: warnings });
    lightingService.deleteMusicMapping(id);
  },

  applyMusicPreset: (presetName) => {
    lightingService.applyMusicPreset(presetName);
  },

  reshuffleMappingSeed: (id) => {
    get().updateMusicMapping(id, { seed: Math.floor(Math.random() * 10000) });
  },

  restartAll: async () => {
    return await lightingService.restartAll();
  },

  initialize: () => {
    // Listen for WebSocket connection changes
    lightingService.onConnectionChange((connected) => {
      set({ engineConnected: connected });
    });

    // Listen for full state broadcasts from Python Engine
    lightingService.onStateChange((state) => {
      const mappings = state.musicMappings && state.musicMappings.length > 0 
        ? state.musicMappings 
        : get().musicMappings;
      const warnings = checkOverlaps(mappings);

      set({
        mode: state.mode,
        outputMode: state.outputMode,
        power_on: state.power_on,
        color: state.color,
        brightness: state.brightness,
        renderBrightness: state.renderBrightness ?? state.brightness,
        connected: state.connected,
        transport: state.transport,
        analyzers: state.analyzers || {},
        musicSettings: (state as any).musicSettings || get().musicSettings,
        musicResponseMode: state.musicResponseMode || (state as any).musicSettings?.response_mode || get().musicResponseMode,
        musicMappings: mappings,
        movieLayout: state.movieLayout || get().movieLayout,
        movieSettings: state.movieSettings || get().movieSettings,
        customEffect: state.customEffect || get().customEffect,
        customConfig: state.customConfig || get().customConfig,
        customSettings: state.customSettings || get().customSettings,
        developerState: (state as any).developer_state || (state as any).developerState || get().developerState,
        developerEvent: (state as any).developer_event || (state as any).developerEvent || get().developerEvent,
        developerEventTimestamp: (state as any).developer_event_timestamp || (state as any).developerEventTimestamp || get().developerEventTimestamp,
        developerZones: (state as any).developer_zones || (state as any).developerZones || get().developerZones,
        developerSettings: (state as any).developer_settings || (state as any).developerSettings || get().developerSettings,
        ledFrame: state.ledFrame,
        ledCount: state.ledCount || DEFAULT_LED_COUNT,
        validationWarnings: warnings,
        audioTelemetry: (state as any).audioTelemetry || get().audioTelemetry
      });
    });

    // Initiate connection to Engine
    lightingService.connect();
  }
}));
