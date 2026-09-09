import React, { useState } from 'react';
import { useLightingStore } from '../store/lightingStore';

export const ExperiencesScreen = () => {
  const { color, brightness, mode, setMode, setColor, setBrightness } = useLightingStore();

  const handleColorChange = (r: number, g: number, b: number) => {
    setColor({ r, g, b });
  };

  const PresetColor = ({ r, g, b, label }: any) => (
    <button 
      onClick={() => handleColorChange(r, g, b)}
      className="flex flex-col items-center gap-2 border-none bg-transparent cursor-pointer"
    >
      <div className="w-12 h-12 rounded-full border-2 border-dev-border-light transition-transform hover:scale-110" style={{ backgroundColor: `rgb(${r},${g},${b})`}}></div>
      <span className="caption">{label}</span>
    </button>
  );

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold tracking-wide mb-8">EXPERIENCES</h1>

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
          <div>
            <h2 className="text-xl font-bold mb-2">CUSTOM LIGHTING</h2>
            <p className="caption mb-8">Take full manual control of your environment.</p>

            <h3 className="text-sm tracking-wide text-dev-text-secondary mb-4 uppercase">Presets</h3>
            <div className="flex gap-6 mb-12">
              <PresetColor r={255} g={0} b={0} label="Red" />
              <PresetColor r={0} g={255} b={0} label="Green" />
              <PresetColor r={0} g={0} b={255} label="Blue" />
              <PresetColor r={255} g={255} b={255} label="White" />
              <PresetColor r={0} g={0} b={0} label="Off" />
              <PresetColor r={139} g={92} b={246} label="DevLights" />
            </div>

            <h3 className="text-sm tracking-wide text-dev-text-secondary mb-4 uppercase">Brightness ({Math.round(brightness)}%)</h3>
            <input 
              type="range" 
              min="0" max="100" 
              value={brightness}
              onChange={(e) => setBrightness(parseInt(e.target.value))}
              className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
            />
          </div>
        )}
        
        {mode !== 'custom' && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <h2 className="text-xl font-bold mb-2 uppercase">{mode} MODE ACTIVE</h2>
            <p className="caption">The lighting engine is actively controlling this experience.</p>
          </div>
        )}
      </div>
    </div>
  );
};
