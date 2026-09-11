import { Plus, Trash2, Shuffle, AlertTriangle, Sparkles, Volume2, Mic, Monitor } from 'lucide-react';
import { useLightingStore, INSTRUMENT_COLORS } from '../store/lightingStore';
import type { MusicInstrument, MusicResponseEffect, MusicDistribution, MusicMapping } from '../types/lighting';

const INSTRUMENTS: { value: MusicInstrument; label: string; desc: string }[] = [
  { value: 'bass', label: 'Bass', desc: 'Low-frequency sub rumble (20–150 Hz)' },
  { value: 'kick', label: 'Kick', desc: 'Punchy low-frequency transient beats' },
  { value: 'clap', label: 'Clap', desc: 'Broadband mid/high transient (1.2–5.5 kHz)' },
  { value: 'vocal', label: 'Vocal', desc: 'Speech & singing formant range (300–3400 Hz)' },
  { value: 'hihat', label: 'Hi-Hat', desc: 'Cymbals & crisp top end (6500–16000 Hz)' },
  { value: 'brass', label: 'Brass', desc: 'Warm horns & harmonic richness (1200–2800 Hz)' },
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
    musicResponseMode,
    setMusicResponseMode,
    addMusicMapping,
    updateMusicMapping,
    deleteMusicMapping,
    applyMusicPreset,
    reshuffleMappingSeed,
    audioTelemetry,
    analyzers,
    audioSource,
    audioDevice,
    availableAudioDevices,
    setMusicAudioSource
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

  const currentSource = audioSource || analyzers?.audio_source || 'system';
  const relevantDevices = availableAudioDevices?.filter(d => d.type === currentSource) || [];
  const currentDeviceName = audioTelemetry?.audio_device || analyzers?.audio_device || audioDevice || (currentSource === 'system' ? 'System Loopback' : 'Default Microphone');
  const isSystemUnavailable = currentSource === 'system' && (audioTelemetry?.audio_status === 'system_audio_unavailable' || analyzers?.audio_status === 'system_audio_unavailable');

  return (
    <div className="space-y-6">
      {/* Presets and Global Controls Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-dev-surface-elevated border border-dev-border-light rounded-2xl p-6">
        <div>
          <h2 className="text-lg font-bold uppercase tracking-wide flex items-center gap-2">
            <Volume2 className="text-dev-primary" size={20} />
            Instrument Mappings
          </h2>
          <p className="caption">
            Map individual instruments & frequency features to independent LED zones.
            <span className="ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-dev-surface border border-dev-border text-dev-text-secondary">
              Style: <strong className="text-dev-primary uppercase">{musicResponseMode}</strong> ({musicResponseMode === 'flash' ? '0% / 100% Binary Flash' : 'Continuous Envelope Fade'})
            </span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Response Style Segmented Switcher: FADE | FLASH */}
          <div className="flex items-center bg-dev-surface-pressed p-1 rounded-xl border border-dev-border">
            <button
              onClick={() => setMusicResponseMode('fade')}
              className={`px-4 py-1.5 text-xs font-bold uppercase tracking-wider rounded-lg transition-all border-none cursor-pointer ${
                musicResponseMode === 'fade'
                  ? 'bg-dev-primary text-white shadow-md ring-1 ring-dev-primary/50'
                  : 'bg-transparent text-dev-text-secondary hover:text-white hover:bg-dev-surface/40'
              }`}
            >
              FADE
            </button>
            <button
              onClick={() => setMusicResponseMode('flash')}
              className={`px-4 py-1.5 text-xs font-bold uppercase tracking-wider rounded-lg transition-all border-none cursor-pointer ${
                musicResponseMode === 'flash'
                  ? 'bg-dev-primary text-white shadow-md ring-1 ring-dev-primary/50'
                  : 'bg-transparent text-dev-text-secondary hover:text-white hover:bg-dev-surface/40'
              }`}
            >
              FLASH
            </button>
          </div>

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

      {/* Audio Source Selector & Live Feature Telemetry */}
      <div className="bg-dev-surface-elevated border border-dev-border-light rounded-2xl p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs font-bold uppercase tracking-wider text-dev-text-secondary">Audio Source:</span>
            
            {/* Pill Toggle: System Audio vs Microphone */}
            <div className="inline-flex bg-dev-surface rounded-xl p-1 border border-dev-border">
              <button
                type="button"
                onClick={() => setMusicAudioSource('system')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all border-none cursor-pointer ${
                  currentSource === 'system'
                    ? 'bg-dev-primary text-white shadow-sm'
                    : 'bg-transparent text-dev-text-muted hover:text-dev-text'
                }`}
              >
                <Monitor size={14} />
                <span>System Audio</span>
              </button>
              <button
                type="button"
                onClick={() => setMusicAudioSource('microphone')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all border-none cursor-pointer ${
                  currentSource === 'microphone'
                    ? 'bg-dev-primary text-white shadow-sm'
                    : 'bg-transparent text-dev-text-muted hover:text-dev-text'
                }`}
              >
                <Mic size={14} />
                <span>Microphone</span>
              </button>
            </div>

            {/* Device Selector (if multiple devices exist) */}
            {relevantDevices.length > 1 ? (
              <select
                value={audioDevice || ''}
                onChange={(e) => setMusicAudioSource(currentSource as any, e.target.value || null)}
                className="bg-dev-surface text-dev-text text-xs rounded-lg px-2.5 py-1.5 border border-dev-border focus:outline-none focus:border-dev-primary cursor-pointer font-mono"
              >
                <option value="">Default {currentSource === 'system' ? 'Loopback' : 'Microphone'}</option>
                {relevantDevices.map((d) => (
                  <option key={d.id} value={d.name}>
                    {d.name} {d.is_default ? '(Default)' : ''}
                  </option>
                ))}
              </select>
            ) : (
              <div className="text-xs text-dev-text-muted flex items-center gap-1.5 bg-dev-surface px-2.5 py-1 rounded-md border border-dev-border/60">
                <span className="font-semibold text-dev-text-secondary">Device:</span>
                <span className="font-mono">{currentDeviceName}</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${
              isSystemUnavailable
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                : 'bg-green-500/20 text-green-300 border border-green-500/40'
            }`}>
              <span className={`w-2 h-2 rounded-full ${
                isSystemUnavailable ? 'bg-amber-400 animate-pulse' : 'bg-green-400'
              }`} />
              {currentSource === 'system'
                ? (isSystemUnavailable ? 'SYSTEM AUDIO MISSING' : 'SYSTEM AUDIO ACTIVE')
                : 'MICROPHONE ACTIVE'}
            </span>

            <div className="text-[11px] text-dev-text-muted font-mono">
              {audioTelemetry?.music_gate_open ? (
                <span className="text-green-400 font-bold">● GATE OPEN</span>
              ) : (
                <span className="text-dev-text-muted">○ GATE CLOSED</span>
              )}
            </div>
          </div>
        </div>

        {/* Informational Guidance based on Source Selection */}
        {isSystemUnavailable && (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3.5 text-xs text-amber-200/90 flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-start gap-2.5 max-w-2xl">
              <AlertTriangle className="text-amber-400 shrink-0 mt-0.5" size={18} />
              <div>
                <p className="font-bold text-amber-300">System Audio Loopback Required for Desktop Capture</p>
                <p className="mt-0.5 text-[11px] text-amber-200/70">
                  macOS requires a virtual loopback device (such as <strong>BlackHole 2ch</strong>) configured in Audio MIDI Setup.
                  Install via Homebrew: <code className="bg-black/40 px-1.5 py-0.5 rounded text-amber-100 font-mono">brew install --cask blackhole-2ch</code> and set up a Multi-Output Device.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setMusicAudioSource('microphone')}
              className="shrink-0 px-3 py-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 font-bold rounded-lg text-xs border border-amber-500/40 transition-colors cursor-pointer flex items-center gap-1.5"
            >
              <Mic size={14} />
              <span>Switch to Mic</span>
            </button>
          </div>
        )}

        {currentSource === 'microphone' && (
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-3 text-xs text-blue-200/80 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Mic size={15} className="text-blue-400 shrink-0" />
              <span>
                Listening to live ambient room audio via <strong>{currentDeviceName}</strong>. No loopback driver is needed.
              </span>
            </div>
            <button
              type="button"
              onClick={() => setMusicAudioSource('system')}
              className="text-[11px] font-semibold text-blue-300 hover:text-white underline ml-3 shrink-0 cursor-pointer bg-transparent border-none"
            >
              Switch to System Audio
            </button>
          </div>
        )}

        {/* Real-time Instrument Detector Telemetry Meters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2.5 pt-1">
          {[
            { key: 'kick', label: 'Kick', val: audioTelemetry?.kick ?? 0, trig: audioTelemetry?.kick_trigger, color: 'bg-orange-500' },
            { key: 'bass', label: 'Bass', val: audioTelemetry?.bass ?? 0, trig: false, color: 'bg-red-500' },
            { key: 'clap', label: 'Clap', val: audioTelemetry?.clap ?? 0, trig: audioTelemetry?.clap_trigger, color: 'bg-yellow-400' },
            { key: 'hihat', label: 'Hi-Hat', val: audioTelemetry?.hihat ?? 0, trig: audioTelemetry?.hihat_trigger, color: 'bg-cyan-400' },
            { key: 'vocal', label: 'Vocal', val: audioTelemetry?.vocal ?? 0, trig: false, color: 'bg-purple-400' },
            { key: 'melody', label: 'Melody', val: audioTelemetry?.melody ?? 0, trig: false, color: 'bg-emerald-400' },
            { key: 'brass', label: 'Brass', val: audioTelemetry?.brass ?? 0, trig: false, color: 'bg-amber-500' }
          ].map((item) => (
            <div key={item.key} className="bg-dev-surface border border-dev-border rounded-lg p-2 flex flex-col justify-between">
              <div className="flex items-center justify-between text-[11px] font-bold">
                <span className="text-dev-text-secondary uppercase">{item.label}</span>
                {item.trig ? (
                  <span className="px-1.5 py-0.2 rounded text-[9px] font-extrabold bg-dev-primary text-white">
                    HIT
                  </span>
                ) : (
                  <span className="text-[10px] font-mono text-dev-text-muted">{Math.round((item.val || 0) * 100)}%</span>
                )}
              </div>
              <div className="w-full bg-dev-surface-pressed h-1.5 rounded-full overflow-hidden mt-1.5">
                <div
                  className={`h-full ${item.color} transition-all duration-75`}
                  style={{ width: `${Math.min(100, Math.max(0, (item.val || 0) * 100))}%` }}
                />
              </div>
            </div>
          ))}
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
