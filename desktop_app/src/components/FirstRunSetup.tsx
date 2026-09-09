import React, { useState } from 'react';
import { useLightingStore } from '../store/lightingStore';
import { Zap, Shield, Monitor, CheckCircle, AlertTriangle } from 'lucide-react';

export const FirstRunSetup = ({ onComplete }: { onComplete: () => void }) => {
  const [step, setStep] = useState(1);
  const engineConnected = useLightingStore(s => s.engineConnected);
  const transport = useLightingStore(s => s.transport);

  return (
    <div className="fixed inset-0 bg-dev-bg z-50 flex items-center justify-center p-8">
      <div className="bg-dev-surface-elevated border border-dev-border rounded-2xl w-full max-w-2xl overflow-hidden flex flex-col h-[600px]">
        
        {/* Header */}
        <div className="p-8 border-b border-dev-border flex items-center gap-4">
          <Zap className="text-dev-primary" size={32} />
          <div>
            <h1 className="text-2xl font-bold">Welcome to DevLights</h1>
            <p className="caption">Turn your screen, music, and code into light.</p>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-8 overflow-y-auto">
          {step === 1 && (
            <div className="space-y-6 animate-in fade-in">
              <h2 className="text-xl font-bold">Preparing DevLights</h2>
              <div className="space-y-4">
                <div className="flex items-center gap-4 p-4 rounded-lg bg-dev-surface">
                  <CheckCircle className="text-dev-success" /> <span>Application Core</span>
                </div>
                <div className="flex items-center gap-4 p-4 rounded-lg bg-dev-surface">
                  <CheckCircle className="text-dev-success" /> <span>Python Lighting Engine</span>
                </div>
                <div className="flex items-center gap-4 p-4 rounded-lg bg-dev-surface">
                  {engineConnected ? <CheckCircle className="text-dev-success" /> : <div className="w-6 h-6 border-2 border-dev-primary border-t-transparent rounded-full animate-spin"></div>}
                  <span>Engine Connection {engineConnected ? 'Established' : 'Connecting...'}</span>
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6 animate-in fade-in">
              <h2 className="text-xl font-bold">Permissions</h2>
              <div className="space-y-4">
                <div className="p-4 rounded-lg border border-dev-border bg-dev-surface">
                  <div className="flex items-center gap-3 mb-2">
                    <Monitor className="text-dev-secondary" />
                    <h3 className="font-bold">Screen Recording</h3>
                  </div>
                  <p className="text-sm text-dev-text-secondary mb-4">Required for Movie and Game mode synchronization.</p>
                  <button className="px-4 py-2 bg-dev-surface-pressed rounded border border-dev-border hover:border-dev-primary transition-colors">
                    Request Permission
                  </button>
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-6 animate-in fade-in">
              <h2 className="text-xl font-bold">Hardware Setup</h2>
              <p className="caption">Connect your DevLights ESP32 Controller via USB.</p>
              
              <div className={`p-6 rounded-lg border flex items-center justify-between
                ${transport === 'usb' ? 'border-dev-success bg-dev-success/10' : 'border-dev-border bg-dev-surface'}
              `}>
                <div>
                  <h3 className="font-bold mb-1">DevLights Controller</h3>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${transport === 'usb' ? 'bg-dev-success' : 'bg-dev-warning animate-pulse'}`}></div>
                    <span className="text-sm text-dev-text-secondary">
                      {transport === 'usb' ? 'Connected via USB' : 'Searching for device...'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-dev-border bg-dev-surface flex justify-between">
          <button 
            onClick={() => setStep(s => Math.max(1, s - 1))}
            className={`px-6 py-2 font-medium rounded text-dev-text-secondary hover:text-dev-text ${step === 1 ? 'opacity-0 pointer-events-none' : ''}`}
          >
            Back
          </button>
          
          <button 
            onClick={() => {
              if (step < 3) setStep(s => s + 1);
              else onComplete();
            }}
            disabled={step === 1 && !engineConnected}
            className="px-8 py-2 bg-dev-primary text-white font-medium rounded hover:bg-dev-primary-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {step === 3 ? 'Start DevLights' : 'Continue'}
          </button>
        </div>
      </div>
    </div>
  );
};
