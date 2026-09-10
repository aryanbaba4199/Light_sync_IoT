import { Plus, Trash2, Shuffle, AlertTriangle, Sparkles, Volume2 } from 'lucide-react';
import { useLightingStore, INSTRUMENT_COLORS } from '../store/lightingStore';
import type { MusicInstrument, MusicResponseEffect, MusicDistribution, MusicMapping } from '../types/lighting';

const INSTRUMENTS: { value: MusicInstrument; label: string; desc: string }[] = [
  { value: 'bass', label: 'Bass', desc: 'Low-frequency sub rumble (20–150 Hz)' },
  { value: 'kick', label: 'Kick', desc: 'Punchy low-frequency transient beats' },
  { value: 'snare', label: 'Snare', desc: 'Mid/high transient impact (250–1500 Hz)' },
  { value: 'vocal', label: 'Vocal', desc: 'Speech & singing formant range (300–3000 Hz)' },
  { value: 'hihat', label: 'Hi-Hat', desc: 'Cymbals & crisp top end (5000–16000 Hz)' },
  { value: 'brass', label: 'Brass', desc: 'Warm horns & harmonic richness' },
  { value: 'melody', label: 'Melody', desc: 'Lead synthesizer and lead pitch energy' },
  { value: 'beat', label: 'Beat', desc: 'General rhythmic transients & downbeats' },
  { value: 'overall', label: 'Overall', desc: 'Full-spectrum audio RMS energy' },
];

const RESPONSES: { value: MusicResponseEffect; label: string }[] = [
  { value: 'static', label: 'Static (Direct)' },
  { value: 'pulse', label: 'Pulse (Attack/Decay)' },
  { value: 'flash', label: 'Flash (Fast Spike)' },
  { value: 'smooth', label: 'Smooth (Sustained)' },
];

const DISTRIBUTIONS: { value: MusicDistribution; label: string }[] = [
  { value: 'zone', label: 'Zone (Continuous)' },
  { value: 'random', label: 'Random (Scattered)' },
];

export const MusicMappingEditor = () => {
  const {
    musicMappings,
    ledCount,
    validationWarnings,
    addMusicMapping,
    updateMusicMapping,
    deleteMusicMapping,
    applyMusicPreset,
    reshuffleMappingSeed
  } = useLightingStore();

  const rgbToHex = (r: number, g: number, b: number) => '#' + [r, g, b].map(x => {
    const hex = x.toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  }).join('');

  const hexToRgb = (hex: string) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : { r: 255, g: 255, b: 255 };
  };

  return (
    <div className="space-y-6">
      {/* Presets and Global Controls Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-dev-surface-elevated border border-dev-border-light rounded-2xl p-6">
        <div>
          <h2 className="text-lg font-bold uppercase tracking-wide flex items-center gap-2">
            <Volume2 className="text-dev-primary" size={20} />
            Instrument Mappings
          </h2>
          <p className="caption">Map individual instruments & frequency features to independent LED zones.</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-dev-surface-pressed p-1 rounded-lg border border-dev-border">
            <span className="text-xs font-semibold px-2 text-dev-text-muted">Presets:</span>
            <button
              onClick={() => applyMusicPreset('default_3_band')}
              className="px-3 py-1.5 text-xs font-semibold rounded-md bg-dev-surface hover:bg-dev-surface-elevated text-dev-text transition-colors border-none cursor-pointer"
            >
              Default 3 Band
            </button>
            <button
              onClick={() => applyMusicPreset('party')}
              className="px-3 py-1.5 text-xs font-semibold rounded-md bg-dev-surface hover:bg-dev-surface-elevated text-dev-text transition-colors border-none cursor-pointer"
            >
              Party
            </button>
            <button
              onClick={() => applyMusicPreset('full_band')}
              className="px-3 py-1.5 text-xs font-semibold rounded-md bg-dev-surface hover:bg-dev-surface-elevated text-dev-text transition-colors border-none cursor-pointer"
            >
              Full Band
            </button>
          </div>

          <button
            onClick={() => addMusicMapping('bass')}
            className="flex items-center gap-2 px-4 py-2 bg-dev-primary text-white font-bold text-xs rounded-lg hover:bg-dev-primary/90 transition-all border-none cursor-pointer shadow-md"
          >
            <Plus size={16} /> Add Instrument
          </button>
        </div>
      </div>

      {/* Validation Warnings Banner */}
      {validationWarnings.length > 0 && (
        <div className="bg-yellow-500/10 border border-yellow-500/40 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="text-yellow-500 shrink-0 mt-0.5" size={20} />
          <div>
            <h4 className="text-sm font-bold text-yellow-400">Zone Overlap Detected</h4>
            <ul className="text-xs text-yellow-300/80 list-disc pl-4 mt-1 space-y-0.5">
              {validationWarnings.map((w, idx) => (
                <li key={idx}>{w}</li>
              ))}
            </ul>
            <p className="text-[11px] text-yellow-400/60 mt-1">
              Adjacent or overlapping LED ranges will blend. Adjust LED ranges to keep zones completely isolated.
            </p>
          </div>
        </div>
      )}

      {/* List of Configured Mappings */}
      <div className="space-y-4">
        {musicMappings.map((m: MusicMapping) => {
          const isInvalidRange = m.startLed > m.endLed || m.startLed < 1 || m.endLed > ledCount;

          return (
            <div
              key={m.id}
              className={`bg-dev-surface-elevated border rounded-xl p-5 transition-all ${
                !m.enabled 
                  ? 'opacity-50 border-dev-border-light' 
                  : isInvalidRange 
                  ? 'border-red-500/60' 
                  : 'border-dev-border-light hover:border-dev-border'
              }`}
            >
              <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
                {/* Instrument Selector */}
                <div className="md:col-span-3">
                  <label className="text-[11px] font-semibold text-dev-text-secondary uppercase mb-1 block">
                    Instrument
                  </label>
                  <select
                    value={m.instrument}
                    onChange={(e) => {
                      const inst = e.target.value as MusicInstrument;
                      updateMusicMapping(m.id, {
                        instrument: inst,
                        color: INSTRUMENT_COLORS[inst] || m.color
                      });
                    }}
                    className="w-full bg-dev-surface border border-dev-border rounded-lg px-3 py-2 text-sm font-bold text-dev-text focus:outline-none focus:border-dev-primary"
                  >
                    {INSTRUMENTS.map(opt => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Color Picker */}
                <div className="md:col-span-1 flex flex-col items-center">
                  <label className="text-[11px] font-semibold text-dev-text-secondary uppercase mb-1 block">
                    Color
                  </label>
                  <input
                    type="color"
                    value={rgbToHex(m.color.r, m.color.g, m.color.b)}
                    onChange={(e) => {
                      const rgb = hexToRgb(e.target.value);
                      updateMusicMapping(m.id, { color: rgb });
                    }}
                    className="w-10 h-9 rounded-lg border border-dev-border cursor-pointer bg-transparent p-0"
                    title="Choose Zone Color"
                  />
                </div>

                {/* LED Range: Start - End */}
                <div className="md:col-span-2">
                  <label className="text-[11px] font-semibold text-dev-text-secondary uppercase mb-1 block">
                    LED Range (1–{ledCount})
                  </label>
                  <div className="flex items-center gap-1.5">
                    <input
                      type="number"
                      min={1}
                      max={ledCount}
                      value={m.startLed}
                      onChange={(e) => {
                        const val = parseInt(e.target.value) || 1;
                        updateMusicMapping(m.id, { startLed: val });
                      }}
                      className="w-16 bg-dev-surface border border-dev-border rounded-lg px-2 py-1.5 text-xs font-mono font-bold text-center text-dev-text"
                    />
                    <span className="text-dev-text-muted text-xs">–</span>
                    <input
                      type="number"
                      min={1}
                      max={ledCount}
                      value={m.endLed}
                      onChange={(e) => {
                        const val = parseInt(e.target.value) || 1;
                        updateMusicMapping(m.id, { endLed: val });
                      }}
                      className="w-16 bg-dev-surface border border-dev-border rounded-lg px-2 py-1.5 text-xs font-mono font-bold text-center text-dev-text"
                    />
                  </div>
                  {isInvalidRange && (
                    <span className="text-[10px] text-red-400 font-semibold block mt-0.5">
                      Invalid LED range
                    </span>
                  )}
                </div>

                {/* Sensitivity Slider */}
                <div className="md:col-span-2">
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-[11px] font-semibold text-dev-text-secondary uppercase">
                      Sensitivity
                    </label>
                    <span className="text-xs font-mono text-dev-text-secondary">
                      {Math.round(m.sensitivity * 100)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min={10}
                    max={200}
                    value={Math.round(m.sensitivity * 100)}
                    onChange={(e) => {
                      const val = parseInt(e.target.value) / 100.0;
                      updateMusicMapping(m.id, { sensitivity: val });
                    }}
                    className="w-full accent-dev-primary h-1.5 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
                  />
                </div>

                {/* Response & Distribution Options */}
                <div className="md:col-span-2 space-y-1.5">
                  <div>
                    <label className="text-[10px] font-semibold text-dev-text-secondary uppercase block">
                      Response
                    </label>
                    <select
                      value={m.response}
                      onChange={(e) => updateMusicMapping(m.id, { response: e.target.value as MusicResponseEffect })}
                      className="w-full bg-dev-surface border border-dev-border rounded px-2 py-1 text-xs text-dev-text"
                    >
                      {RESPONSES.map(r => (
                        <option key={r.value} value={r.value}>{r.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex items-center gap-1">
                    <select
                      value={m.distribution}
                      onChange={(e) => updateMusicMapping(m.id, { distribution: e.target.value as MusicDistribution })}
                      className="w-full bg-dev-surface border border-dev-border rounded px-2 py-1 text-xs text-dev-text"
                    >
                      {DISTRIBUTIONS.map(d => (
                        <option key={d.value} value={d.value}>{d.label}</option>
                      ))}
                    </select>
                    {m.distribution === 'random' && (
                      <button
                        onClick={() => reshuffleMappingSeed(m.id)}
                        className="p-1 rounded bg-dev-surface hover:bg-dev-surface-pressed text-dev-text-secondary border border-dev-border cursor-pointer"
                        title="Reshuffle Random Seed"
                      >
                        <Shuffle size={12} />
                      </button>
                    )}
                  </div>
                </div>

                {/* Toggle Enable & Delete */}
                <div className="md:col-span-2 flex items-center justify-end gap-3">
                  <button
                    onClick={() => updateMusicMapping(m.id, { enabled: !m.enabled })}
                    className={`px-3 py-1 rounded-md text-xs font-bold border transition-colors cursor-pointer ${
                      m.enabled 
                        ? 'bg-dev-primary/20 text-dev-primary border-dev-primary/40' 
                        : 'bg-dev-surface text-dev-text-muted border-dev-border'
                    }`}
                  >
                    {m.enabled ? 'ON' : 'OFF'}
                  </button>

                  <button
                    onClick={() => deleteMusicMapping(m.id)}
                    className="p-1.5 text-dev-text-muted hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors border-none bg-transparent cursor-pointer"
                    title="Delete Mapping"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          );
        })}

        {musicMappings.length === 0 && (
          <div className="p-8 text-center bg-dev-surface border border-dashed border-dev-border rounded-xl">
            <Sparkles className="mx-auto text-dev-text-muted mb-2" size={28} />
            <h4 className="font-bold text-dev-text">No Mappings Configured</h4>
            <p className="caption mt-1 mb-4">Add your first instrument mapping or select a preset above.</p>
            <button
              onClick={() => applyMusicPreset('default_3_band')}
              className="px-4 py-2 bg-dev-primary text-white text-xs font-bold rounded-lg border-none cursor-pointer"
            >
              Load Default 3 Band
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
