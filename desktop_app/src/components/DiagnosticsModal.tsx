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
