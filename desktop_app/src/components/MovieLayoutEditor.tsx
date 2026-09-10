import React from 'react';
import { useLightingStore } from '../store/lightingStore';
import { Film, Music2, Sparkles, Sliders, CheckCircle, AlertTriangle } from 'lucide-react';

export const MovieLayoutEditor: React.FC = () => {
  const {
    movieLayout,
    movieSettings,
    ledCount,
    setMovieLayout,
    setMovieMusicSync,
    setMovieSamplingThickness,
  } = useLightingStore();

  const top = movieLayout?.top ?? 100;
  const right = movieLayout?.right ?? 50;
  const bottom = movieLayout?.bottom ?? 100;
  const left = movieLayout?.left ?? 50;
  const total = top + right + bottom + left;
  const thickness = movieLayout?.sampling_thickness ?? 0.10;
  const syncMusic = movieSettings?.sync_music ?? false;

  const handleEdgeChange = (edge: 'top' | 'right' | 'bottom' | 'left', val: number) => {
    const clamped = Math.max(0, Math.min(ledCount, val));
    setMovieLayout({ [edge]: clamped });
  };

  const applyPreset = (t: number, r: number, b: number, l: number) => {
    setMovieLayout({ top: t, right: r, bottom: b, left: l });
  };

  const isCountExact = total === ledCount;

  return (
    <div className="space-y-6">
      {/* Header with Title & Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Film className="text-dev-primary" size={20} />
            <h2 className="text-xl font-bold tracking-wide">SPATIAL MOVIE MODE</h2>
          </div>
          <p className="caption text-dev-text-muted">
            Configure physical LED perimeter placement around your TV or monitor for true spatial backlighting.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`text-xs px-3 py-1.5 rounded-full border font-mono font-medium flex items-center gap-1.5 ${
              isCountExact
                ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-400'
                : 'bg-amber-950/40 border-amber-800/60 text-amber-400'
            }`}
          >
            {isCountExact ? <CheckCircle size={13} /> : <AlertTriangle size={13} />}
            {total} / {ledCount} Bulbs
          </span>
        </div>
      </div>

      {/* Visual Perimeter Layout Card */}
      <div className="bg-dev-surface-elevated border border-dev-border-light rounded-2xl p-6 relative overflow-hidden">
        <div className="text-xs font-bold uppercase tracking-wider text-dev-text-secondary mb-4 flex items-center justify-between">
          <span>Perimeter Geometry Preview</span>
          <span className="text-[11px] text-dev-text-muted font-mono font-normal">Clockwise Direction</span>
        </div>

        {/* The Monitor / TV representation */}
        <div className="relative max-w-lg mx-auto aspect-[16/9] bg-black/80 rounded-xl border-2 border-dev-border p-4 flex flex-col justify-between shadow-2xl">
          {/* Ambient Screen Glow in center */}
          <div className="absolute inset-0 bg-gradient-to-tr from-dev-primary/5 via-blue-500/5 to-purple-500/5 rounded-xl pointer-events-none" />

          {/* TOP EDGE BAR */}
          <div className="flex flex-col items-center">
            <div className="flex items-center gap-2 bg-dev-surface-pressed/90 border border-dev-border px-3 py-1 rounded-full text-xs font-bold shadow">
              <span className="text-dev-text-secondary uppercase tracking-wider">Top</span>
              <span className="text-dev-primary font-mono">{top} bulbs</span>
            </div>
            <div className="w-full h-1.5 mt-2 bg-gradient-to-r from-dev-primary/40 via-dev-primary to-dev-primary/40 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.6)]" />
          </div>

          {/* MIDDLE ROW (LEFT EDGE & RIGHT EDGE) */}
          <div className="flex items-center justify-between my-auto px-2">
            {/* LEFT EDGE BAR */}
            <div className="flex items-center gap-2">
              <div className="h-28 w-1.5 bg-gradient-to-b from-dev-primary/40 via-dev-primary to-dev-primary/40 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.6)]" />
              <div className="bg-dev-surface-pressed/90 border border-dev-border px-2.5 py-1 rounded-full text-xs font-bold shadow flex flex-col items-center">
                <span className="text-[10px] text-dev-text-secondary uppercase tracking-wider">Left</span>
                <span className="text-dev-primary font-mono">{left}</span>
              </div>
            </div>

            {/* SCREEN CENTER CONTENT GRAPHIC */}
            <div className="text-center pointer-events-none opacity-80">
              <Film className="mx-auto mb-1 text-dev-text-muted" size={28} />
              <span className="text-[11px] font-medium tracking-wide uppercase text-dev-text-muted">
                Spatial Video Content
              </span>
              <div className="text-[10px] text-dev-text-muted/60 mt-0.5">
                Each edge independently sampled
              </div>
            </div>

            {/* RIGHT EDGE BAR */}
            <div className="flex items-center gap-2">
              <div className="bg-dev-surface-pressed/90 border border-dev-border px-2.5 py-1 rounded-full text-xs font-bold shadow flex flex-col items-center">
                <span className="text-[10px] text-dev-text-secondary uppercase tracking-wider">Right</span>
                <span className="text-dev-primary font-mono">{right}</span>
              </div>
              <div className="h-28 w-1.5 bg-gradient-to-b from-dev-primary/40 via-dev-primary to-dev-primary/40 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.6)]" />
            </div>
          </div>

          {/* BOTTOM EDGE BAR */}
          <div className="flex flex-col items-center">
            <div className="w-full h-1.5 mb-2 bg-gradient-to-r from-dev-primary/40 via-dev-primary to-dev-primary/40 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.6)]" />
            <div className="flex items-center gap-2 bg-dev-surface-pressed/90 border border-dev-border px-3 py-1 rounded-full text-xs font-bold shadow">
              <span className="text-dev-text-secondary uppercase tracking-wider">Bottom</span>
              <span className="text-dev-primary font-mono">{bottom} bulbs</span>
            </div>
          </div>
        </div>
      </div>

      {/* Perimeter Controls Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Top Bulbs', edge: 'top' as const, val: top },
          { label: 'Right Bulbs', edge: 'right' as const, val: right },
          { label: 'Bottom Bulbs', edge: 'bottom' as const, val: bottom },
          { label: 'Left Bulbs', edge: 'left' as const, val: left },
        ].map(({ label, edge, val }) => (
          <div key={edge} className="bg-dev-surface-elevated border border-dev-border-light rounded-xl p-4">
            <label className="caption text-dev-text-secondary block mb-1 uppercase tracking-wider">
              {label}
            </label>
            <div className="flex items-center gap-2 mt-2">
              <button
                type="button"
                onClick={() => handleEdgeChange(edge, val - 5)}
                className="w-8 h-8 rounded-lg bg-dev-surface-pressed border border-dev-border hover:bg-dev-surface text-dev-text font-bold text-sm transition-colors flex items-center justify-center shrink-0"
                title="Decrease 5 bulbs"
              >
                -
              </button>
              <input
                type="number"
                min="0"
                max={ledCount}
                value={val}
                onChange={(e) => handleEdgeChange(edge, parseInt(e.target.value) || 0)}
                className="w-full text-center bg-dev-surface border border-dev-border rounded-lg py-1 text-sm font-mono font-bold text-dev-text focus:outline-none focus:border-dev-primary"
              />
              <button
                type="button"
                onClick={() => handleEdgeChange(edge, val + 5)}
                className="w-8 h-8 rounded-lg bg-dev-surface-pressed border border-dev-border hover:bg-dev-surface text-dev-text font-bold text-sm transition-colors flex items-center justify-center shrink-0"
                title="Increase 5 bulbs"
              >
                +
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Preset Layouts */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-dev-text-muted mr-1 font-semibold uppercase tracking-wider">Presets:</span>
        <button
          type="button"
          onClick={() => applyPreset(100, 50, 100, 50)}
          className="px-3 py-1.5 rounded-lg bg-dev-surface-pressed border border-dev-border hover:border-dev-primary/60 text-xs text-dev-text font-medium transition-colors"
        >
          Default (100 · 50 · 100 · 50)
        </button>
        <button
          type="button"
          onClick={() => applyPreset(75, 75, 75, 75)}
          className="px-3 py-1.5 rounded-lg bg-dev-surface-pressed border border-dev-border hover:border-dev-primary/60 text-xs text-dev-text font-medium transition-colors"
        >
          Square (75 · 75 · 75 · 75)
        </button>
        <button
          type="button"
          onClick={() => applyPreset(105, 45, 105, 45)}
          className="px-3 py-1.5 rounded-lg bg-dev-surface-pressed border border-dev-border hover:border-dev-primary/60 text-xs text-dev-text font-medium transition-colors"
        >
          16:9 Widescreen (105 · 45 · 105 · 45)
        </button>
        <button
          type="button"
          onClick={() => applyPreset(120, 30, 120, 30)}
          className="px-3 py-1.5 rounded-lg bg-dev-surface-pressed border border-dev-border hover:border-dev-primary/60 text-xs text-dev-text font-medium transition-colors"
        >
          21:9 Ultrawide (120 · 30 · 120 · 30)
        </button>
      </div>

      {/* Sampling Depth & Sync Music Settings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Sampling Thickness */}
        <div className="bg-dev-surface-elevated border border-dev-border-light rounded-xl p-5">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Sliders size={16} className="text-dev-primary" />
              <label className="text-sm font-bold text-dev-text">Edge Sampling Depth</label>
            </div>
            <span className="text-xs font-mono font-bold text-dev-primary">
              {Math.round(thickness * 100)}%
            </span>
          </div>
          <p className="caption text-dev-text-muted mb-4">
            Percentage of active screen width/height sampled along each perimeter edge.
          </p>
          <input
            type="range"
            min="4"
            max="25"
            step="1"
            value={Math.round(thickness * 100)}
            onChange={(e) => setMovieSamplingThickness(parseInt(e.target.value) / 100)}
            className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
          />
        </div>

        {/* Sync Music Toggle */}
        <div className="bg-dev-surface-elevated border border-dev-border-light rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Music2 size={16} className={syncMusic ? 'text-dev-primary' : 'text-dev-text-muted'} />
                <label className="text-sm font-bold text-dev-text flex items-center gap-2">
                  Sync Music
                  {syncMusic && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-dev-primary/20 text-dev-primary font-mono font-semibold">
                      ACTIVE
                    </span>
                  )}
                </label>
              </div>

              {/* Toggle Switch */}
              <button
                type="button"
                role="switch"
                aria-checked={syncMusic}
                onClick={() => setMovieMusicSync(!syncMusic)}
                className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-200 cursor-pointer ${
                  syncMusic ? 'bg-dev-primary' : 'bg-dev-surface-pressed border border-dev-border'
                }`}
              >
                <div
                  className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-200 ${
                    syncMusic ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            <p className="caption text-dev-text-muted mt-1 leading-relaxed">
              Sync Music uses music intensity to modulate brightness while video continues controlling spatial color.
            </p>
          </div>

          <div className="mt-3 pt-3 border-t border-dev-border-light/60 flex items-center gap-2 text-[11px] text-dev-text-muted">
            <Sparkles size={12} className="text-dev-primary shrink-0" />
            <span>Cinematic response: loud beats brighten, quiet scenes dim smoothly without pumping.</span>
          </div>
        </div>
      </div>
    </div>
  );
};
