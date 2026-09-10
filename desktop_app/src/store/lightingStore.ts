import { create } from 'zustand';
import type { LightingMode, RGBColor, TransportType, OutputMode } from '../types/lighting';
import { lightingService } from '../services';

interface LightingStore {
  mode: LightingMode;
  outputMode: OutputMode;
  power_on: boolean;
  color: RGBColor;
  brightness: number;
  renderBrightness: number;
  connected: boolean;
  transport: TransportType;
  engineConnected: boolean; // Is the python websocket connected?
  analyzers: {
    screen_analyzer?: string;
  };
  
  // Actions
  setMode: (mode: LightingMode) => void;
  setOutputMode: (mode: OutputMode) => void;
  setPower: (isOn: boolean) => void;
  setColor: (color: RGBColor) => void;
  setBrightness: (brightness: number) => void;
  initialize: () => void;
}

export const useLightingStore = create<LightingStore>((set) => ({
  mode: 'custom',
  outputMode: 'auto',
  power_on: true,
  color: { r: 255, g: 0, b: 0 },
  brightness: 100,
  renderBrightness: 100,
  connected: false,
  transport: 'none',
  engineConnected: false,
  analyzers: {},

  setMode: (mode) => {
    lightingService.setMode(mode);
    set({ mode }); // optimistic update
  },
  
  setOutputMode: (mode) => {
    lightingService.setOutputMode(mode);
    set({ outputMode: mode });
  },

  setPower: (isOn) => {
    lightingService.setPower(isOn);
    set({ power_on: isOn });
  },

  setColor: (color) => {
    lightingService.setColor(color);
    set({ color }); // optimistic update
  },
  
  setBrightness: (brightness) => {
    lightingService.setBrightness(brightness);
    set({ brightness }); // optimistic update
  },

  initialize: () => {
    // Listen for WebSocket connection changes
    lightingService.onConnectionChange((connected) => {
      set({ engineConnected: connected });
    });

    // Listen for full state broadcasts from Python Engine
    lightingService.onStateChange((state) => {
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
      });
    });

    // Initiate connection to Engine
    lightingService.connect();
  }
}));
