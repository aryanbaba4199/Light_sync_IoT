import { useState } from 'react';
import { useLightingStore } from '../store/lightingStore';
import { LedStripPreview300 } from '../components/LedStripPreview300';
import { MusicMappingEditor } from '../components/MusicMappingEditor';
import { MovieLayoutEditor } from '../components/MovieLayoutEditor';
import { CustomEffectEditor } from '../components/CustomEffectEditor';
import { DeveloperModePanel } from '../components/DeveloperModePanel';

export const ExperiencesScreen = () => {
  const { mode, setMode, restartAll } = useLightingStore();
  const [isRestarting, setIsRestarting] = useState(false);

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold tracking-wide">EXPERIENCES</h1>
        <button
          onClick={async () => {
            setIsRestarting(true);
            await restartAll();
            setTimeout(() => setIsRestarting(false), 1500);
          }}
          disabled={isRestarting}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-950/40 hover:bg-red-900/60 text-red-300 border border-red-800/60 text-xs font-semibold cursor-pointer transition-all disabled:opacity-50"
          title="Physically reboots ESP32, clears LED strip, and resets the lighting engine"
        >
          <svg className={`w-3.5 h-3.5 ${isRestarting ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {isRestarting ? 'Restarting...' : 'Restart Lights & Hardware'}
        </button>
      </div>

      <div className="flex gap-4 mb-8">
        {['movie', 'music', 'game', 'developer', 'custom'].map((m) => (
          <button 
            key={m}
            onClick={() => setMode(m as any)}
            className={`px-6 py-2 rounded-full uppercase tracking-wider text-sm font-bold transition-all border-none cursor-pointer
              ${mode === m ? 'bg-dev-primary text-white' : 'bg-dev-surface-elevated text-dev-text-secondary hover:text-dev-text'}`}
          >
            {m}
          </button>
        ))}
      </div>

      <div className="bg-dev-surface-elevated border border-dev-border-light rounded-2xl p-8">
        {mode === 'custom' && (
          <CustomEffectEditor />
        )}
        
        {mode === 'music' && (
          <div className="space-y-8">
            <LedStripPreview300 />
            <MusicMappingEditor />
          </div>
        )}

        {mode === 'movie' && (
          <MovieLayoutEditor />
        )}

        {mode === 'developer' && (
          <DeveloperModePanel />
        )}

        {mode === 'game' && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <h2 className="text-xl font-bold mb-2 uppercase">{mode} MODE ACTIVE</h2>
            <p className="caption">The lighting engine is actively controlling this experience.</p>
          </div>
        )}
      </div>
    </div>
  );
};
