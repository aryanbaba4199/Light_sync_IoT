import React from 'react';
import { useLightingStore } from '../store/lightingStore';
import type { CustomEffectType, RGBColor } from '../types/lighting';

interface EffectMeta {
  id: CustomEffectType;
  name: string;
  desc: string;
  badge?: string;
  icon: string;
}

const EFFECTS: EffectMeta[] = [
  { id: 'rainfall', name: 'Rainfall', desc: 'Active LEDs bounce 1 to 300 with fading gradient trail', badge: 'HERO', icon: '🌧️' },
  { id: 'flash', name: 'Flash', desc: 'Instant ON/OFF strobe with per-cycle color stability', icon: '⚡' },
  { id: 'random', name: 'Random', desc: 'Stochastic constellations that hold position between intervals', icon: '✨' },
  { id: 'wave', name: 'Wave', desc: 'Smooth sinusoidal traveling wave across the perimeter', icon: '🌊' },
  { id: 'comet', name: 'Comet', desc: 'High-intensity head with exponential trailing particle decay', icon: '☄️' },
  { id: 'breathing', name: 'Breathing', desc: 'Ultra-smooth global ambient sine pulse with easing', icon: '🫁' },
  { id: 'sparkle', name: 'Sparkle', desc: 'Ambient starfield with random flares and individual lifetimes', icon: '🌟' },
  { id: 'color_chase', name: 'Color Chase', desc: 'Sequential multi-color block trains with configurable gaps', icon: '🏎️' },
  { id: 'fire', name: 'Fire', desc: 'Procedural thermodynamic heat simulation with ember flicker', icon: '🔥' },
  { id: 'rainbow_flow', name: 'Rainbow Flow', desc: 'Continuous HSV spectrum wave traveling seamlessly', icon: '🌈' },
  { id: 'static', name: 'Static Solid', desc: 'Clean uniform color across the entire installation', icon: '💡' },
];

export const CustomEffectEditor: React.FC = () => {
  const {
    customEffect,
    customConfig,
    brightness,
    ledFrame,
    ledCount,
    setCustomEffect,
    setCustomEffectConfig,
    setBrightness
  } = useLightingStore();

  const cfg = customConfig || {};

  const rgbToHex = (c?: RGBColor) => {
    if (!c) return '#0078ff';
    const r = Math.max(0, Math.min(255, c.r || 0));
    const g = Math.max(0, Math.min(255, c.g || 0));
    const b = Math.max(0, Math.min(255, c.b || 0));
    return '#' + [r, g, b].map(x => x.toString(16).padStart(2, '0')).join('');
  };

  const hexToRgb = (hex: string): RGBColor => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : { r: 255, g: 255, b: 255 };
  };

  const updateCfg = (patch: Record<string, any>) => {
    setCustomEffectConfig(customEffect, patch);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold tracking-wide mb-1">CUSTOM ANIMATION EFFECTS</h2>
        <p className="caption">
          Procedural multi-effect engine rendered natively across {ledCount} LEDs via Protocol V2.
        </p>
      </div>

      {/* Live 300-LED Matrix Preview */}
      <div className="p-4 bg-black/60 rounded-xl border border-dev-border-light shadow-inner">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-dev-text-secondary uppercase tracking-wider">
            Live Strip Matrix (60 Display Slices)
          </span>
          <span className="text-[10px] text-dev-text-muted font-mono uppercase">
            Effect: {customEffect.replace('_', ' ')}
          </span>
        </div>
        <div 
          className="grid gap-[3px]"
          style={{ gridTemplateColumns: 'repeat(60, minmax(0, 1fr))' }}
        >
          {Array.from({ length: 60 }).map((_, i) => {
            const rgb = (ledFrame && ledFrame[i]) ? ledFrame[i] : [15, 15, 20];
            const [r, g, b] = rgb;
            const isLit = r > 10 || g > 10 || b > 10;
            return (
              <div
                key={i}
                title={`Slice #${i + 1} (RGB: ${r}, ${g}, ${b})`}
                className="h-3 rounded-[2px] transition-colors duration-75"
                style={{
                  backgroundColor: `rgb(${r}, ${g}, ${b})`,
                  boxShadow: isLit ? `0 0 5px rgba(${r}, ${g}, ${b}, 0.8)` : 'none'
                }}
              />
            );
          })}
        </div>
      </div>

      {/* Effect Selection Grid */}
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-dev-text-secondary mb-3">
          Select Animation Effect
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {EFFECTS.map((eff) => {
            const isSelected = customEffect === eff.id;
            return (
              <button
                key={eff.id}
                type="button"
                onClick={() => setCustomEffect(eff.id)}
                className={`flex flex-col text-left p-3.5 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-dev-primary/15 border-dev-primary text-white shadow-lg shadow-dev-primary/10'
                    : 'bg-dev-surface border-dev-border-light text-dev-text-secondary hover:text-dev-text hover:border-dev-border'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5 w-full">
                  <span className="text-lg">{eff.icon}</span>
                  {eff.badge && (
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-dev-primary text-white tracking-widest">
                      {eff.badge}
                    </span>
                  )}
                </div>
                <div className="font-bold text-sm text-dev-text mb-1">{eff.name}</div>
                <div className="text-[11px] text-dev-text-muted leading-tight line-clamp-2">{eff.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Contextual Effect Controls */}
      <div className="bg-dev-surface border border-dev-border-light rounded-2xl p-6 space-y-6">
        <h3 className="text-xs font-bold uppercase tracking-widest text-dev-primary">
          {customEffect.replace('_', ' ')} Settings
        </h3>

        {/* 1. RAINFALL CONTROLS */}
        {customEffect === 'rainfall' && (
          <div className="space-y-5">
            <div className="flex items-center gap-4">
              <input
                type="color"
                value={rgbToHex(cfg.color)}
                onChange={(e) => updateCfg({ color: hexToRgb(e.target.value) })}
                className="w-12 h-12 rounded-lg cursor-pointer border-none p-0"
              />
              <div>
                <div className="text-sm font-semibold">Drop Color</div>
                <div className="caption">Color of bouncing lead raindrop and gradient trail</div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Speed</span>
                <span className="font-mono">{cfg.speed ?? 50}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="100"
                value={cfg.speed ?? 50}
                onChange={(e) => updateCfg({ speed: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Active LED Count</span>
                <span className="font-mono">{cfg.active_led_count ?? 10} LEDs</span>
              </div>
              <input
                type="range"
                min="1"
                max="30"
                value={cfg.active_led_count ?? 10}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  updateCfg({ active_led_count: val, trail_length: val });
                }}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>
        )}

        {/* 2. FLASH CONTROLS */}
        {customEffect === 'flash' && (
          <div className="space-y-5">
            <div>
              <label className="block text-xs font-semibold mb-2">Color Mode</label>
              <div className="flex gap-2">
                {(['random', 'single', 'palette'] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => updateCfg({ color_mode: m })}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider cursor-pointer transition-all border ${
                      (cfg.color_mode ?? 'random') === m
                        ? 'bg-dev-primary text-white border-dev-primary'
                        : 'bg-dev-surface-elevated text-dev-text-secondary border-dev-border'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            {cfg.color_mode === 'single' && (
              <div className="flex items-center gap-4">
                <input
                  type="color"
                  value={rgbToHex(cfg.color)}
                  onChange={(e) => updateCfg({ color: hexToRgb(e.target.value) })}
                  className="w-12 h-12 rounded-lg cursor-pointer border-none p-0"
                />
                <div>
                  <div className="text-sm font-semibold">Strobe Color</div>
                  <div className="caption">Full strip flash color</div>
                </div>
              </div>
            )}

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Flash Frequency</span>
                <span className="font-mono">{cfg.speed ?? 40}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="100"
                value={cfg.speed ?? 40}
                onChange={(e) => updateCfg({ speed: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>
        )}

        {/* 3. RANDOM CONTROLS */}
        {customEffect === 'random' && (
          <div className="space-y-5">
            <div>
              <label className="block text-xs font-semibold mb-2">Color Mode</label>
              <div className="flex gap-2">
                {(['random', 'palette', 'single'] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => updateCfg({ color_mode: m })}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider cursor-pointer transition-all border ${
                      (cfg.color_mode ?? 'random') === m
                        ? 'bg-dev-primary text-white border-dev-primary'
                        : 'bg-dev-surface-elevated text-dev-text-secondary border-dev-border'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            {cfg.color_mode === 'single' && (
              <div className="flex items-center gap-4">
                <input
                  type="color"
                  value={rgbToHex(cfg.color)}
                  onChange={(e) => updateCfg({ color: hexToRgb(e.target.value) })}
                  className="w-12 h-12 rounded-lg cursor-pointer border-none p-0"
                />
                <div className="text-sm font-semibold">Constellation Color</div>
              </div>
            )}

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Active Dots</span>
                <span className="font-mono">{cfg.active_led_count ?? 20} LEDs</span>
              </div>
              <input
                type="range"
                min="5"
                max="60"
                value={cfg.active_led_count ?? 20}
                onChange={(e) => updateCfg({ active_led_count: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Change Interval / Speed</span>
                <span className="font-mono">{cfg.speed ?? 35}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="100"
                value={cfg.speed ?? 35}
                onChange={(e) => updateCfg({ speed: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={cfg.fade ?? true}
                onChange={(e) => updateCfg({ fade: e.target.checked })}
                className="accent-dev-primary w-4 h-4 rounded cursor-pointer"
              />
              <span className="text-xs font-semibold">Smooth cross-fade transitions between shifts</span>
            </label>
          </div>
        )}

        {/* 4. WAVE CONTROLS */}
        {customEffect === 'wave' && (
          <div className="space-y-5">
            <div className="flex gap-6 items-center">
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  value={rgbToHex(cfg.color)}
                  onChange={(e) => updateCfg({ color: hexToRgb(e.target.value) })}
                  className="w-10 h-10 rounded-lg cursor-pointer border-none p-0"
                />
                <span className="text-xs font-semibold">Crest Color</span>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  value={rgbToHex(cfg.background_color)}
                  onChange={(e) => updateCfg({ background_color: hexToRgb(e.target.value) })}
                  className="w-10 h-10 rounded-lg cursor-pointer border-none p-0"
                />
                <span className="text-xs font-semibold">Trough Color</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Wave Speed</span>
                <span className="font-mono">{cfg.speed ?? 40}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="100"
                value={cfg.speed ?? 40}
                onChange={(e) => updateCfg({ speed: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Wavelength</span>
                <span className="font-mono">{cfg.width ?? 60} LEDs</span>
              </div>
              <input
                type="range"
                min="20"
                max="150"
                value={cfg.width ?? 60}
                onChange={(e) => updateCfg({ width: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold mb-2">Travel Direction</label>
              <div className="flex gap-2">
                {(['forward', 'backward'] as const).map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => updateCfg({ direction: d })}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase cursor-pointer border ${
                      (cfg.direction ?? 'forward') === d
                        ? 'bg-dev-primary text-white border-dev-primary'
                        : 'bg-dev-surface-elevated text-dev-text-secondary border-dev-border'
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 5. COMET CONTROLS */}
        {customEffect === 'comet' && (
          <div className="space-y-5">
            <div className="flex items-center gap-4">
              <input
                type="color"
                value={rgbToHex(cfg.color)}
                onChange={(e) => updateCfg({ color: hexToRgb(e.target.value) })}
                className="w-12 h-12 rounded-lg cursor-pointer border-none p-0"
              />
              <div className="text-sm font-semibold">Comet Head Color</div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Velocity</span>
                <span className="font-mono">{cfg.speed ?? 50}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="100"
                value={cfg.speed ?? 50}
                onChange={(e) => updateCfg({ speed: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Tail Length</span>
                <span className="font-mono">{cfg.tail_length ?? 25} LEDs</span>
              </div>
              <input
                type="range"
                min="5"
                max="60"
                value={cfg.tail_length ?? 25}
                onChange={(e) => updateCfg({ tail_length: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold mb-2">Movement Pattern</label>
              <div className="flex gap-2">
                {(['bounce', 'forward', 'backward'] as const).map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => updateCfg({ direction: d })}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase cursor-pointer border ${
                      (cfg.direction ?? 'bounce') === d
                        ? 'bg-dev-primary text-white border-dev-primary'
                        : 'bg-dev-surface-elevated text-dev-text-secondary border-dev-border'
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 6. BREATHING CONTROLS */}
        {customEffect === 'breathing' && (
          <div className="space-y-5">
            <div className="flex items-center gap-4">
              <input
                type="color"
                value={rgbToHex(cfg.color)}
                onChange={(e) => updateCfg({ color: hexToRgb(e.target.value) })}
                className="w-12 h-12 rounded-lg cursor-pointer border-none p-0"
              />
              <div className="text-sm font-semibold">Pulse Color</div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Breathing Pace</span>
                <span className="font-mono">{cfg.speed ?? 30}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="100"
                value={cfg.speed ?? 30}
                onChange={(e) => updateCfg({ speed: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>
        )}

        {/* 7. SPARKLE CONTROLS */}
        {customEffect === 'sparkle' && (
          <div className="space-y-5">
            <div className="flex gap-6 items-center">
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  value={rgbToHex(cfg.color)}
                  onChange={(e) => updateCfg({ color: hexToRgb(e.target.value) })}
                  className="w-10 h-10 rounded-lg cursor-pointer border-none p-0"
                />
                <span className="text-xs font-semibold">Sparkle Color</span>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  value={rgbToHex(cfg.background_color)}
                  onChange={(e) => updateCfg({ background_color: hexToRgb(e.target.value) })}
                  className="w-10 h-10 rounded-lg cursor-pointer border-none p-0"
                />
                <span className="text-xs font-semibold">Ambient Bed</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Sparkle Activity Rate</span>
                <span className="font-mono">{cfg.speed ?? 50}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="100"
                value={cfg.speed ?? 50}
                onChange={(e) => updateCfg({ speed: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>
        )}

        {/* 8. COLOR CHASE CONTROLS */}
        {customEffect === 'color_chase' && (
          <div className="space-y-5">
            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Speed</span>
                <span className="font-mono">{cfg.speed ?? 45}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="100"
                value={cfg.speed ?? 45}
                onChange={(e) => updateCfg({ speed: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Block Size</span>
                <span className="font-mono">{cfg.group_size ?? 15} LEDs</span>
              </div>
              <input
                type="range"
                min="5"
                max="40"
                value={cfg.group_size ?? 15}
                onChange={(e) => updateCfg({ group_size: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Spacing Gap</span>
                <span className="font-mono">{cfg.gap ?? 10} LEDs</span>
              </div>
              <input
                type="range"
                min="0"
                max="30"
                value={cfg.gap ?? 10}
                onChange={(e) => updateCfg({ gap: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>
        )}

        {/* 9. FIRE CONTROLS */}
        {customEffect === 'fire' && (
          <div className="space-y-5">
            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Heat / Flame Energy</span>
                <span className="font-mono">{cfg.heat ?? 70}%</span>
              </div>
              <input
                type="range"
                min="20"
                max="100"
                value={cfg.heat ?? 70}
                onChange={(e) => updateCfg({ heat: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Ember Flicker</span>
                <span className="font-mono">{cfg.flicker ?? 60}%</span>
              </div>
              <input
                type="range"
                min="10"
                max="100"
                value={cfg.flicker ?? 60}
                onChange={(e) => updateCfg({ flicker: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>
        )}

        {/* 10. RAINBOW FLOW CONTROLS */}
        {customEffect === 'rainbow_flow' && (
          <div className="space-y-5">
            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Wave Speed</span>
                <span className="font-mono">{cfg.speed ?? 40}%</span>
              </div>
              <input
                type="range"
                min="5"
                max="100"
                value={cfg.speed ?? 40}
                onChange={(e) => updateCfg({ speed: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Spectrum Wavelength</span>
                <span className="font-mono">{cfg.wavelength ?? 150} LEDs</span>
              </div>
              <input
                type="range"
                min="50"
                max="300"
                value={cfg.wavelength ?? 150}
                onChange={(e) => updateCfg({ wavelength: parseInt(e.target.value) })}
                className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>
        )}

        {/* 11. STATIC SOLID CONTROLS */}
        {customEffect === 'static' && (
          <div className="space-y-5">
            <div className="flex items-center gap-4">
              <input
                type="color"
                value={rgbToHex(cfg.color)}
                onChange={(e) => updateCfg({ color: hexToRgb(e.target.value) })}
                className="w-12 h-12 rounded-lg cursor-pointer border-none p-0"
              />
              <div className="text-sm font-semibold">Solid Color</div>
            </div>
          </div>
        )}
      </div>

      {/* Global Brightness Slider */}
      <div className="bg-dev-surface border border-dev-border-light rounded-2xl p-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs font-bold uppercase tracking-wider text-dev-text-secondary">
            Master Brightness
          </span>
          <span className="text-sm font-bold font-mono text-dev-text">
            {Math.round(brightness)}%
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={brightness}
          onChange={(e) => setBrightness(parseInt(e.target.value))}
          className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
        />
      </div>
    </div>
  );
};
