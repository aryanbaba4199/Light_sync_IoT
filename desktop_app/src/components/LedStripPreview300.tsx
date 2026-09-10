import { useMemo } from 'react';
import { useLightingStore } from '../store/lightingStore';
import type { MusicMapping } from '../types/lighting';

export const LedStripPreview300 = () => {
  const { musicMappings, ledCount } = useLightingStore();

  // Compute color for each of the 300 LEDs
  const ledColors = useMemo(() => {
    const colors: { r: number; g: number; b: number; label?: string }[] = Array.from(
      { length: ledCount },
      () => ({ r: 18, g: 18, b: 24 }) // off/dim state
    );

    const enabledMappings = musicMappings.filter(m => m.enabled);

    enabledMappings.forEach(mapping => {
      const { startLed, endLed, color, distribution, seed } = mapping;
      const s = Math.max(1, Math.min(ledCount, startLed));
      const e = Math.max(1, Math.min(ledCount, endLed));
      if (s > e) return;

      if (distribution === 'random') {
        // Deterministic pseudo-random selection
        const rangeIndices: number[] = [];
        for (let idx = s - 1; idx < e; idx++) {
          rangeIndices.push(idx);
        }
        // Deterministic shuffle with seed
        let currentSeed = seed || 42;
        const pseudoRand = () => {
          currentSeed = (currentSeed * 9301 + 49297) % 233280;
          return currentSeed / 233280;
        };
        for (let i = rangeIndices.length - 1; i > 0; i--) {
          const j = Math.floor(pseudoRand() * (i + 1));
          [rangeIndices[i], rangeIndices[j]] = [rangeIndices[j], rangeIndices[i]];
        }
        rangeIndices.forEach(idx => {
          colors[idx] = { r: color.r, g: color.g, b: color.b, label: mapping.instrument };
        });
      } else {
        // Continuous Zone distribution
        for (let idx = s - 1; idx < e; idx++) {
          colors[idx] = { r: color.r, g: color.g, b: color.b, label: mapping.instrument };
        }
      }
    });

    return colors;
  }, [musicMappings, ledCount]);

  // Zone segments for layout overview
  const activeZones = useMemo(() => {
    return musicMappings
      .filter(m => m.enabled && m.startLed <= m.endLed)
      .sort((a, b) => a.startLed - b.startLed);
  }, [musicMappings]);

  return (
    <div className="bg-dev-surface-elevated border border-dev-border-light rounded-2xl p-6 mb-8">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider text-dev-text">300 LED Strip Layout</h3>
          <p className="caption">Visual representation of real physical strip LED zones (1–{ledCount})</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2.5 py-1 rounded-full bg-dev-surface border border-dev-border text-dev-text-secondary font-mono">
            {activeZones.length} Active Zones · {ledCount} LEDs
          </span>
        </div>
      </div>

      {/* 300 LED Grid Matrix (30 columns x 10 rows for clean dense visualization) */}
      <div className="p-3 bg-black/60 rounded-xl border border-dev-border-light shadow-inner mb-6">
        <div 
          className="grid gap-[3px]"
          style={{
            gridTemplateColumns: 'repeat(60, minmax(0, 1fr))'
          }}
        >
          {ledColors.map((c, i) => (
            <div
              key={i}
              title={`LED #${i + 1}${c.label ? ` · ${c.label.toUpperCase()}` : ' (Unassigned)'}`}
              className="h-2 rounded-[1.5px] transition-colors duration-150 cursor-pointer hover:scale-150 hover:z-20 relative"
              style={{
                backgroundColor: `rgb(${c.r}, ${c.g}, ${c.b})`,
                boxShadow: c.r > 20 || c.g > 20 || c.b > 20 ? `0 0 3px rgba(${c.r}, ${c.g}, ${c.b}, 0.8)` : 'none'
              }}
            />
          ))}
        </div>
      </div>

      {/* Linear Zone Strip Overview with Labels */}
      <div>
        <div className="text-xs font-semibold text-dev-text-secondary uppercase mb-2">Zone Allocation Map</div>
        <div className="h-7 w-full bg-dev-surface-pressed rounded-lg overflow-hidden flex border border-dev-border relative mb-3">
          {activeZones.map((z: MusicMapping) => {
            const widthPct = ((z.endLed - z.startLed + 1) / ledCount) * 100;
            const leftPct = ((z.startLed - 1) / ledCount) * 100;
            return (
              <div
                key={z.id}
                className="absolute top-0 bottom-0 flex items-center justify-center px-1 overflow-hidden transition-all duration-200"
                style={{
                  left: `${leftPct}%`,
                  width: `${widthPct}%`,
                  backgroundColor: `rgba(${z.color.r}, ${z.color.g}, ${z.color.b}, 0.85)`,
                  borderLeft: '1px solid rgba(255,255,255,0.3)',
                  borderRight: '1px solid rgba(255,255,255,0.3)'
                }}
                title={`${z.instrument.toUpperCase()}: LEDs ${z.startLed}–${z.endLed}`}
              >
                <span className="text-[10px] font-bold text-black truncate drop-shadow-sm select-none">
                  {widthPct > 5 ? z.instrument.toUpperCase() : ''}
                </span>
              </div>
            );
          })}
        </div>

        {/* Labels underneath for each zone */}
        <div className="flex flex-wrap gap-3 mt-2">
          {activeZones.map((z: MusicMapping) => (
            <div 
              key={z.id}
              className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-dev-surface border border-dev-border text-xs"
            >
              <div 
                className="w-2.5 h-2.5 rounded-full" 
                style={{ backgroundColor: `rgb(${z.color.r}, ${z.color.g}, ${z.color.b})` }}
              />
              <span className="font-bold text-dev-text capitalize">{z.instrument}</span>
              <span className="text-dev-text-muted font-mono">LED {z.startLed}–{z.endLed}</span>
              {z.distribution === 'random' && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-dev-surface-pressed text-dev-text-secondary">
                  Random
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
