import React from 'react';
import { Film, Music, Gamepad2, Code, Sliders, MonitorPlay, Zap } from 'lucide-react';
import { useLightingStore } from '../store/lightingStore';
import type { LightingMode } from '../types/lighting';
import { VirtualStrip } from '../components/VirtualStrip';

const ExpCard = ({ icon: Icon, title, desc, modeId, isActive, onClick }: any) => {
  return (
    <div 
      onClick={onClick}
      className={`p-4 rounded-xl border transition-all duration-200 cursor-pointer flex items-center gap-4
      ${isActive 
        ? 'bg-dev-surface-pressed border-dev-primary' 
        : 'bg-dev-surface-elevated border-dev-border-light hover:border-dev-border'
      }`}
    >
    <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0
      ${isActive ? 'bg-dev-primary text-dev-bg' : 'bg-dev-surface-pressed text-dev-primary'}
    `}>
      <Icon size={24} />
    </div>
    <div>
      <div className={`font-medium ${isActive ? 'text-dev-primary' : 'text-dev-text'}`}>{title}</div>
      <div className="caption">{desc}</div>
    </div>
  </div>
  );
};

export const DashboardScreen = () => {
  const { color, brightness, mode, setMode, setBrightness, outputMode, setOutputMode, transport, engineConnected, analyzers } = useLightingStore();


  return (
    <div className="p-8 max-w-4xl mx-auto">
      <header className="mb-8 flex justify-between items-end">
        <h1 className="text-2xl font-bold tracking-wide">AMBIENT NOW</h1>
        
        {/* Output Selector */}
        <div className="flex bg-dev-surface-pressed rounded-lg p-1">
          {['auto', 'virtual', 'esp32'].map(opt => (
            <button
              key={opt}
              onClick={() => setOutputMode(opt as any)}
              className={`px-3 py-1 text-xs font-medium rounded-md uppercase tracking-wider transition-colors ${
                outputMode === opt ? 'bg-dev-surface-elevated text-dev-text shadow-sm' : 'text-dev-text-muted hover:text-dev-text-secondary'
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      </header>
      
      {analyzers?.screen_analyzer === 'permission_denied' && mode === 'movie' && (
        <div className="mb-8 bg-red-500/10 border border-red-500/50 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center shrink-0">
              <MonitorPlay className="text-red-500" size={20} />
            </div>
            <div>
              <h3 className="font-semibold text-red-400">Screen Recording Permission Required</h3>
              <p className="text-sm text-red-400/80 mt-1">
                DevLights needs Screen Recording access to synchronize lighting with your screen.
              </p>
            </div>
          </div>
          <button 
            onClick={() => {
              // Usually handled by opening system preferences, but we just hint it for now
              alert("Please open System Settings -> Privacy & Security -> Screen Recording and allow DevLights/Terminal/Python.");
            }}
            className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 text-sm font-medium rounded-lg transition-colors"
          >
            Open Settings
          </button>
        </div>
      )}

      <VirtualStrip />

      <section className="mb-12">
        <div className="bg-dev-surface-elevated border border-dev-border-light rounded-2xl p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
            <div>
              <div className="caption">RGB</div>
              <h3 className="text-xl font-bold">{color?.r || 0} · {color?.g || 0} · {color?.b || 0}</h3>
            </div>
            <div>
              <div className="caption">Brightness</div>
              <h3 className="text-xl font-bold">{Math.round(brightness)}%</h3>
            </div>
            <div>
              <div className="caption">Hardware Output</div>
              <div className="flex items-center gap-2 mt-1">
                <div className={`w-2 h-2 rounded-full ${transport === 'usb' ? 'bg-green-500' : 'bg-yellow-500'}`} />
                <h3 className="text-sm font-semibold uppercase">{transport === 'usb' ? 'ESP32 Connected' : 'Virtual Mode'}</h3>
              </div>
            </div>
            <div>
              <div className="caption">Engine</div>
              <div className="flex items-center gap-2 mt-1">
                <div className={`w-2 h-2 rounded-full ${engineConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                <h3 className="text-sm font-semibold uppercase">{engineConnected ? 'Running' : 'Disconnected'}</h3>
              </div>
            </div>
            {mode === 'movie' && (
              <div>
                <div className="caption">Analyzer</div>
                <div className="flex items-center gap-2 mt-1">
                  <div className={`w-2 h-2 rounded-full ${analyzers?.screen_analyzer === 'running' ? 'bg-green-500' : analyzers?.screen_analyzer === 'permission_denied' ? 'bg-red-500' : 'bg-yellow-500'}`} />
                  <h3 className="text-sm font-semibold uppercase">{analyzers?.screen_analyzer || 'Unknown'}</h3>
                </div>
              </div>
            )}
          </div>
          
          <div className="w-full">
            <input 
              type="range" 
              min="0" max="100" 
              value={brightness}
              onChange={(e) => setBrightness(parseInt(e.target.value))}
              className="w-full accent-dev-primary h-2 bg-dev-surface-pressed rounded-lg appearance-none cursor-pointer"
            />
          </div>
        </div>
      </section>

      <section>
        <h3 className="text-lg font-semibold tracking-wide mb-4">YOUR EXPERIENCES</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <ExpCard icon={Film} title="Movie" desc="Fill the room with the scene." modeId="movie" isActive={mode === 'movie'} onClick={() => setMode('movie')} />
          <ExpCard icon={Music} title="Music" desc="Turn sound into light." modeId="music" isActive={mode === 'music'} onClick={() => setMode('music')} />
          <ExpCard icon={Gamepad2} title="Game" desc="React to every moment." modeId="game" isActive={mode === 'game'} onClick={() => setMode('game')} />
          <ExpCard icon={Code} title="Developer" desc="Your code has a pulse." modeId="developer" isActive={mode === 'developer'} onClick={() => setMode('developer')} />
          <ExpCard icon={Sliders} title="Custom" desc="Your light. Your rules." modeId="custom" isActive={mode === 'custom'} onClick={() => setMode('custom')} />
        </div>
      </section>
    </div>
  );
};
