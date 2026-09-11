import type { ILightingService } from './LightingService';
import type { LightingMode, RGBColor, LightingState, MusicResponseMode, CustomEffectType, CustomEffectConfig } from '../types/lighting';

export class MockLightingService implements ILightingService {
  private state: LightingState = {
    mode: 'movie',
    color: { r: 139, g: 92, b: 246 },
    brightness: 74,
    connected: true,
    transport: 'none',
    outputMode: 'auto',
    power_on: true,
    customEffect: 'rainfall',
    customConfig: { speed: 50, active_led_count: 10, trail_length: 10 }
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

  async setPower(isOn: boolean): Promise<void> {
    this.state.power_on = isOn;
    this.notifyState();
  }

  async setOutputMode(_mode: string): Promise<void> {}

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

  async setMusicColors(bass?: RGBColor, mid?: RGBColor, treb?: RGBColor): Promise<void> {
    this.state.musicSettings = {
      bass_color: bass || this.state.musicSettings?.bass_color,
      mid_color: mid || this.state.musicSettings?.mid_color,
      treb_color: treb || this.state.musicSettings?.treb_color
    };
    this.notifyState();
  }

  async setMusicMappings(mappings: any[]): Promise<void> {
    this.state.musicMappings = mappings;
    this.notifyState();
  }

  async setMusicMapping(mapping: any): Promise<void> {
    const list = this.state.musicMappings || [];
    const idx = list.findIndex(m => m.id === mapping.id);
    if (idx >= 0) {
      list[idx] = mapping;
    } else {
      list.push(mapping);
    }
    this.state.musicMappings = [...list];
    this.notifyState();
  }

  async deleteMusicMapping(id: string): Promise<void> {
    this.state.musicMappings = (this.state.musicMappings || []).filter(m => m.id !== id);
    this.notifyState();
  }

  async applyMusicPreset(presetName: string): Promise<void> {
    console.log('[MockService] Applied preset', presetName);
    this.notifyState();
  }

  async setMusicResponseMode(mode: MusicResponseMode): Promise<void> {
    this.state.musicResponseMode = mode;
    this.state.musicSettings = {
      ...(this.state.musicSettings || {}),
      response_mode: mode
    };
    this.notifyState();
  }

  async setMusicAudioSource(source: 'system' | 'microphone', device?: string | null): Promise<void> {
    this.state.musicSettings = {
      ...(this.state.musicSettings || {}),
      audio_source: source,
      system_audio_device: device ?? null
    };
    if (this.state.analyzers) {
      this.state.analyzers.audio_source = source;
      this.state.analyzers.audio_device = device || (source === 'system' ? 'System Loopback' : 'Microphone');
      this.state.analyzers.audio_status = 'ready';
    }
    this.notifyState();
  }

  async setMovieLayout(layout: any): Promise<void> {
    this.state.movieLayout = layout;
    this.notifyState();
  }

  async setMovieMusicSync(enabled: boolean): Promise<void> {
    this.state.movieSettings = {
      ...(this.state.movieSettings || {}),
      sync_music: enabled
    };
    this.notifyState();
  }

  async setMovieSettings(settings: any): Promise<void> {
    this.state.movieSettings = {
      ...(this.state.movieSettings || {}),
      ...settings
    };
    this.notifyState();
  }

  async setMovieMonitor(monitorIndex: number): Promise<void> {
    this.state.movieSettings = {
      ...(this.state.movieSettings || {}),
      monitor_index: monitorIndex
    };
    this.notifyState();
  }

  async setCustomEffect(effect: CustomEffectType): Promise<void> {
    this.state.customEffect = effect;
    this.notifyState();
  }

  async setCustomEffectConfig(effect: CustomEffectType, config: CustomEffectConfig): Promise<void> {
    this.state.customEffect = effect;
    this.state.customConfig = {
      ...(this.state.customConfig || {}),
      ...config
    };
    this.notifyState();
  }

  async triggerDeveloperEvent(event: string, _priority?: number, _duration?: number): Promise<void> {
    this.state.developerState = (event.includes('BUILD') ? 'BUILDING' : event.includes('TEST') ? 'TESTING' : 'IDLE') as any;
    this.state.developerEvent = event;
    this.state.developerEventTimestamp = Date.now() / 1000;
    this.notifyState();
  }

  async restartAll(): Promise<boolean> {
    console.log('[MockService] Restarted all');
    this.notifyState();
    return true;
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
