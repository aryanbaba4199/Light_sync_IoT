import { useState } from 'react';
import { DiagnosticsModal } from '../components/DiagnosticsModal';
import { Terminal, Shield, RefreshCw, Power } from 'lucide-react';
import { useLightingStore } from '../store/lightingStore';

export const SettingsScreen = () => {
  const [showDiag, setShowDiag] = useState(false);
  const [isRestarting, setIsRestarting] = useState(false);
  const { restartAll } = useLightingStore();

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold tracking-wide mb-8">SETTINGS</h1>

      <div className="space-y-6">
        <div className="bg-dev-surface-elevated border border-dev-border-light rounded-2xl overflow-hidden">
          <div className="p-6 border-b border-dev-border">
            <h3 className="font-bold text-lg mb-1">Application</h3>
            <p className="caption">Manage DevLights desktop preferences.</p>
          </div>
          <div className="p-2">
            <button className="w-full flex items-center justify-between p-4 hover:bg-dev-surface rounded-lg text-left transition-colors cursor-pointer border-none bg-transparent">
              <div className="flex items-center gap-4">
                <div className="p-2 bg-dev-surface-pressed rounded-lg text-dev-text"><RefreshCw size={20} /></div>
                <div>
                  <div className="font-medium text-dev-text">Check for Updates</div>
                  <div className="caption">Version 1.0.0 is up to date</div>
                </div>
              </div>
            </button>
            <button className="w-full flex items-center justify-between p-4 hover:bg-dev-surface rounded-lg text-left transition-colors cursor-pointer border-none bg-transparent">
              <div className="flex items-center gap-4">
                <div className="p-2 bg-dev-surface-pressed rounded-lg text-dev-text"><Shield size={20} /></div>
                <div>
                  <div className="font-medium text-dev-text">Permissions</div>
                  <div className="caption">Manage Screen and Audio access</div>
                </div>
              </div>
            </button>
          </div>
        </div>

        <div className="bg-dev-surface-elevated border border-dev-border-light rounded-2xl overflow-hidden">
          <div className="p-6 border-b border-dev-border">
            <h3 className="font-bold text-lg mb-1">Advanced</h3>
            <p className="caption">Troubleshooting and developer tools.</p>
          </div>
          <div className="p-2">
            <button 
              onClick={() => setShowDiag(true)}
              className="w-full flex items-center justify-between p-4 hover:bg-dev-surface rounded-lg text-left transition-colors cursor-pointer border-none bg-transparent"
            >
              <div className="flex items-center gap-4">
                <div className="p-2 bg-dev-surface-pressed rounded-lg text-dev-secondary"><Terminal size={20} /></div>
                <div>
                  <div className="font-medium text-dev-text">System Diagnostics</div>
                  <div className="caption">View engine state and hardware logs</div>
                </div>
              </div>
            </button>
            <button 
              onClick={async () => {
                setIsRestarting(true);
                await restartAll();
                setTimeout(() => setIsRestarting(false), 1500);
              }}
              disabled={isRestarting}
              className="w-full flex items-center justify-between p-4 hover:bg-red-950/30 rounded-lg text-left transition-colors cursor-pointer border-none bg-transparent"
            >
              <div className="flex items-center gap-4">
                <div className="p-2 bg-red-950/50 text-red-400 rounded-lg"><Power size={20} /></div>
                <div>
                  <div className="font-medium text-red-400">{isRestarting ? 'Restarting Hardware & Engine...' : 'Restart Lights & Hardware'}</div>
                  <div className="caption">Reboots ESP32 micro-controller, clears LED strip, and resets lighting engine</div>
                </div>
              </div>
            </button>
          </div>
        </div>
      </div>

      {showDiag && <DiagnosticsModal onClose={() => setShowDiag(false)} />}
    </div>
  );
};
