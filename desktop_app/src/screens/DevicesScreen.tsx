import { useLightingStore } from '../store/lightingStore';
import { Cpu, Usb, Activity } from 'lucide-react';

export const DevicesScreen = () => {
  const { connected, transport } = useLightingStore();

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold tracking-wide mb-8">DEVICES</h1>

      <div className={`bg-dev-surface-elevated border rounded-2xl p-6 flex items-center justify-between transition-colors
        ${connected ? 'border-dev-success/50' : 'border-dev-border-light'}
      `}>
        <div className="flex items-center gap-6">
          <div className={`w-16 h-16 rounded-full flex items-center justify-center shrink-0
            ${connected ? 'bg-dev-success/20 text-dev-success' : 'bg-dev-surface-pressed text-dev-text-secondary'}
          `}>
            <Cpu size={32} />
          </div>
          <div>
            <h3 className="font-bold text-lg mb-1">DevLights Controller</h3>
            <div className="flex items-center gap-4 caption">
              <span className="flex items-center gap-1"><Usb size={14} /> {transport.toUpperCase()}</span>
              <span>ESP32_WROOM_32</span>
            </div>
          </div>
        </div>

        <div className="text-right">
          <div className="flex items-center justify-end gap-2 mb-1">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-dev-success' : 'bg-dev-error animate-pulse'}`}></div>
            <span className={`font-bold ${connected ? 'text-dev-success' : 'text-dev-error'}`}>
              {connected ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>
          <p className="caption flex items-center justify-end gap-1"><Activity size={14} /> Firmware v1.0.0</p>
        </div>
      </div>
    </div>
  );
};
