import { useLightingStore } from '../store/lightingStore';
import { X, Copy } from 'lucide-react';

export const DiagnosticsModal = ({ onClose }: { onClose: () => void }) => {
  const state = useLightingStore();

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(state, null, 2));
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-8 backdrop-blur-sm">
      <div className="bg-dev-bg border border-dev-border rounded-xl w-full max-w-3xl flex flex-col h-[700px] shadow-2xl">
        
        <div className="p-4 border-b border-dev-border flex items-center justify-between bg-dev-surface rounded-t-xl">
          <h2 className="font-bold text-lg">System Diagnostics</h2>
          <button onClick={onClose} className="p-2 hover:bg-dev-surface-pressed rounded-lg text-dev-text-secondary">
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-dev-surface-elevated p-4 rounded-lg border border-dev-border">
              <span className="caption block mb-1">UI Version</span>
              <span className="font-mono text-sm">1.0.0-desktop</span>
            </div>
            <div className="bg-dev-surface-elevated p-4 rounded-lg border border-dev-border">
              <span className="caption block mb-1">Engine Connection</span>
              <span className={`font-mono text-sm ${state.engineConnected ? 'text-dev-success' : 'text-dev-error'}`}>
                {state.engineConnected ? 'CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>
            <div className="bg-dev-surface-elevated p-4 rounded-lg border border-dev-border">
              <span className="caption block mb-1">Hardware Transport</span>
              <span className="font-mono text-sm">{state.transport.toUpperCase()}</span>
            </div>
            <div className="bg-dev-surface-elevated p-4 rounded-lg border border-dev-border">
              <span className="caption block mb-1">Active Experience</span>
              <span className="font-mono text-sm">{state.mode.toUpperCase()}</span>
            </div>
          </div>

          {/* AUDIO ANALYSIS V2 TELEMETRY CARD */}
          <div className="bg-dev-surface-elevated p-5 rounded-lg border border-dev-border space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-sm text-dev-text">Audio Analysis V2 Telemetry</h3>
                <span className="caption text-xs">Real-time noise floor rejection & transient onset detectors</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="caption text-xs">Music Gate:</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                  state.audioTelemetry?.music_gate_open 
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' 
                    : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                }`}>
                  {state.audioTelemetry?.music_gate_open ? 'OPEN (ACTIVE)' : 'CLOSED (IDLE)'}
                </span>
              </div>
            </div>

            {/* Transient Trigger Badges */}
            <div className="flex items-center gap-3 pt-1">
              <span className="caption text-xs">Transients:</span>
              <div className={`px-2.5 py-1 rounded text-xs font-mono font-bold transition-all ${
                state.audioTelemetry?.kick_trigger 
                  ? 'bg-red-500 text-white shadow-lg shadow-red-500/50 scale-105' 
                  : 'bg-dev-surface text-zinc-500 border border-dev-border'
              }`}>
                KICK
              </div>
              <div className={`px-2.5 py-1 rounded text-xs font-mono font-bold transition-all ${
                state.audioTelemetry?.snare_trigger 
                  ? 'bg-amber-500 text-black shadow-lg shadow-amber-500/50 scale-105' 
                  : 'bg-dev-surface text-zinc-500 border border-dev-border'
              }`}>
                SNARE
              </div>
              <div className={`px-2.5 py-1 rounded text-xs font-mono font-bold transition-all ${
                state.audioTelemetry?.hihat_trigger 
                  ? 'bg-cyan-400 text-black shadow-lg shadow-cyan-400/50 scale-105' 
                  : 'bg-dev-surface text-zinc-500 border border-dev-border'
              }`}>
                HI-HAT
              </div>
            </div>

            {/* Live Feature Meters */}
            <div className="grid grid-cols-4 gap-3 pt-2">
              {[
                { name: 'Bass', val: state.audioTelemetry?.bass ?? 0 },
                { name: 'Kick', val: state.audioTelemetry?.kick ?? 0 },
                { name: 'Snare', val: state.audioTelemetry?.snare ?? 0 },
                { name: 'Hi-Hat', val: state.audioTelemetry?.hihat ?? 0 },
                { name: 'Vocal', val: state.audioTelemetry?.vocal ?? 0 },
                { name: 'Melody', val: state.audioTelemetry?.melody ?? 0 },
                { name: 'Beat', val: state.audioTelemetry?.beat ?? 0 },
                { name: 'Overall', val: state.audioTelemetry?.overall ?? 0 }
              ].map(feat => (
                <div key={feat.name} className="bg-dev-surface p-2.5 rounded border border-dev-border">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="caption">{feat.name}</span>
                    <span className="font-mono text-dev-text font-bold">{(feat.val * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                    <div 
                      className="bg-dev-primary h-full transition-all duration-75"
                      style={{ width: `${Math.min(100, Math.max(0, feat.val * 100))}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="font-bold mb-2">Engine State Dump</h3>
            <pre className="bg-[#050505] p-4 rounded-lg border border-dev-border overflow-x-auto text-xs text-dev-primary-light font-mono leading-relaxed">
              {JSON.stringify({
                color: state.color,
                brightness: state.brightness,
                transport: state.transport,
                platform: navigator.platform,
                userAgent: navigator.userAgent
              }, null, 2)}
            </pre>
          </div>
        </div>

        <div className="p-4 border-t border-dev-border bg-dev-surface flex justify-end rounded-b-xl">
          <button 
            onClick={handleCopy}
            className="flex items-center gap-2 px-4 py-2 bg-dev-surface-pressed hover:bg-dev-border rounded border border-dev-border transition-colors"
          >
            <Copy size={16} />
            <span>Copy Diagnostics</span>
          </button>
        </div>

      </div>
    </div>
  );
};
