import React, { useState } from 'react';
import { useLightingStore } from '../store/lightingStore';
import type { RGBColor } from '../types/lighting';

export const ExperiencesScreen = () => {
  const { color, brightness, mode, setMode, setColor, setBrightness, musicSettings, setMusicColors } = useLightingStore();
  const [activeBand, setActiveBand] = useState<string>('bass');
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

  const handleColorChange = (r: number, g: number, b: number) => {
    setColor({ r, g, b });
  };

  const handleMusicColorChange = (r: number, g: number, b: number) => {
    if (activeBand === 'bass') setMusicColors({r,g,b}, undefined, undefined);
    if (activeBand === 'mid') setMusicColors(undefined, {r,g,b}, undefined);
    if (activeBand === 'treb') setMusicColors(undefined, undefined, {r,g,b});
  };

  const PresetColor = ({ r, g, b, label, onClick }: any) => (
    <button 
      onClick={onClick || (() => handleColorChange(r, g, b))}
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

            <h3 className="text-sm tracking-wide text-dev-text-secondary mb-4 uppercase">Color Picker</h3>
            <div className="flex gap-6 mb-12 items-center">
              <input 
                type="color" 
                value={rgbToHex(color.r, color.g, color.b)}
                onChange={(e) => {
                  const {r,g,b} = hexToRgb(e.target.value);
                  handleColorChange(r, g, b);
                }}
                style={{ width: '80px', height: '80px', padding: 0, border: 'none', borderRadius: '12px', cursor: 'pointer' }}
              />
              <p className="caption">Click the square to open the OS color picker and choose any color combination!</p>
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
        
        {mode === 'music' && (
          <div>
            <h2 className="text-xl font-bold mb-2 uppercase">MUSIC FREQUENCY MAPPING</h2>
            <p className="caption mb-8">Assign colors to different sound frequencies.</p>

            <div className="flex gap-4 mb-8">
               <button 
                  onClick={() => setActiveBand('bass')}
                  className={`px-6 py-2 rounded-lg font-bold border-none cursor-pointer ${activeBand === 'bass' ? 'bg-dev-primary text-white' : 'bg-dev-surface text-dev-text-secondary'}`}
                  style={{ borderBottom: activeBand === 'bass' ? `4px solid rgb(${musicSettings?.bass_color?.r||255}, ${musicSettings?.bass_color?.g||0}, ${musicSettings?.bass_color?.b||0})` : 'none'}}
                >
                 BASS (LOW)
               </button>
               <button 
                  onClick={() => setActiveBand('mid')}
                  className={`px-6 py-2 rounded-lg font-bold border-none cursor-pointer ${activeBand === 'mid' ? 'bg-dev-primary text-white' : 'bg-dev-surface text-dev-text-secondary'}`}
                  style={{ borderBottom: activeBand === 'mid' ? `4px solid rgb(${musicSettings?.mid_color?.r||0}, ${musicSettings?.mid_color?.g||255}, ${musicSettings?.mid_color?.b||0})` : 'none'}}
                >
                 VOCALS (MID)
               </button>
               <button 
                  onClick={() => setActiveBand('treb')}
                  className={`px-6 py-2 rounded-lg font-bold border-none cursor-pointer ${activeBand === 'treb' ? 'bg-dev-primary text-white' : 'bg-dev-surface text-dev-text-secondary'}`}
                  style={{ borderBottom: activeBand === 'treb' ? `4px solid rgb(${musicSettings?.treb_color?.r||0}, ${musicSettings?.treb_color?.g||0}, ${musicSettings?.treb_color?.b||255})` : 'none'}}
                >
                 MELODY (HIGH)
               </button>
            </div>

            <h3 className="text-sm tracking-wide text-dev-text-secondary mb-4 uppercase">Color Picker for {activeBand}</h3>
            <div className="flex gap-6 mb-12 items-center">
              <input 
                type="color" 
                value={activeBand === 'bass' ? rgbToHex(musicSettings?.bass_color?.r||255, musicSettings?.bass_color?.g||0, musicSettings?.bass_color?.b||0) : activeBand === 'mid' ? rgbToHex(musicSettings?.mid_color?.r||0, musicSettings?.mid_color?.g||255, musicSettings?.mid_color?.b||0) : rgbToHex(musicSettings?.treb_color?.r||0, musicSettings?.treb_color?.g||0, musicSettings?.treb_color?.b||255)}
                onChange={(e) => {
                  const {r,g,b} = hexToRgb(e.target.value);
                  handleMusicColorChange(r, g, b);
                }}
                style={{ width: '80px', height: '80px', padding: 0, border: 'none', borderRadius: '12px', cursor: 'pointer' }}
              />
              <p className="caption">Click the square to pick an exact color for this frequency!</p>
            </div>

          </div>
        )}

        {(mode === 'movie' || mode === 'game' || mode === 'developer') && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <h2 className="text-xl font-bold mb-2 uppercase">{mode} MODE ACTIVE</h2>
            <p className="caption">The lighting engine is actively controlling this experience.</p>
          </div>
        )}
      </div>
    </div>
  );
};
