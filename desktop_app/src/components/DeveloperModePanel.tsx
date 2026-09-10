import React from 'react';
import { useLightingStore } from '../store/lightingStore';
import { LedStripPreview300 } from './LedStripPreview300';
import { Code, Terminal, CheckCircle2, AlertTriangle, XCircle, GitCommit, GitPullRequest, Rocket, Play, RefreshCw } from 'lucide-react';

export const DeveloperModePanel: React.FC = () => {
  const {
    developerState,
    developerEvent,
    triggerDeveloperEvent,
  } = useLightingStore();

  const stateColors: Record<string, { bg: string; text: string; border: string }> = {
    IDLE: { bg: 'bg-blue-950/40', text: 'text-blue-400', border: 'border-blue-800/50' },
    CODING: { bg: 'bg-cyan-950/40', text: 'text-cyan-300', border: 'border-cyan-700/50' },
    BUILDING: { bg: 'bg-amber-950/40', text: 'text-amber-400', border: 'border-amber-700/50' },
    TESTING: { bg: 'bg-purple-950/40', text: 'text-purple-300', border: 'border-purple-700/50' },
    DEPLOYING: { bg: 'bg-teal-950/40', text: 'text-teal-300', border: 'border-teal-700/50' },
  };

  const currentStateStyle = stateColors[developerState] || stateColors.IDLE;

  const quickActions = [
    { label: 'Coding Pulse', event: 'CODING_ACTIVITY', icon: Code, color: 'hover:bg-cyan-900/40 text-cyan-300 border-cyan-800/40' },
    { label: 'File Saved', event: 'FILE_SAVED', icon: Code, color: 'hover:bg-cyan-900/40 text-cyan-300 border-cyan-800/40' },
    { label: 'Build Start', event: 'BUILD_STARTED', icon: Play, color: 'hover:bg-amber-900/40 text-amber-300 border-amber-800/40' },
    { label: 'Build Pass', event: 'BUILD_SUCCESS', icon: CheckCircle2, color: 'hover:bg-green-900/40 text-green-300 border-green-800/40' },
    { label: 'Build Fail', event: 'BUILD_FAILED', icon: XCircle, color: 'hover:bg-red-900/40 text-red-300 border-red-800/40' },
    { label: 'Test Start', event: 'TEST_STARTED', icon: Play, color: 'hover:bg-purple-900/40 text-purple-300 border-purple-800/40' },
    { label: 'Test Pass', event: 'TEST_SUCCESS', icon: CheckCircle2, color: 'hover:bg-green-900/40 text-green-300 border-green-800/40' },
    { label: 'Test Fail', event: 'TEST_FAILED', icon: XCircle, color: 'hover:bg-red-900/40 text-red-300 border-red-800/40' },
    { label: 'Git Commit', event: 'GIT_COMMIT', icon: GitCommit, color: 'hover:bg-blue-900/40 text-blue-300 border-blue-800/40' },
    { label: 'Git Push', event: 'GIT_PUSH', icon: RefreshCw, color: 'hover:bg-blue-900/40 text-blue-300 border-blue-800/40' },
    { label: 'PR Merged', event: 'PR_MERGED', icon: GitPullRequest, color: 'hover:bg-emerald-900/40 text-emerald-300 border-emerald-800/40' },
    { label: 'Deploy Start', event: 'DEPLOY_STARTED', icon: Rocket, color: 'hover:bg-teal-900/40 text-teal-300 border-teal-800/40' },
    { label: 'Deploy Pass', event: 'DEPLOY_SUCCESS', icon: CheckCircle2, color: 'hover:bg-green-900/40 text-green-300 border-green-800/40' },
    { label: 'Warning', event: 'WARNING', icon: AlertTriangle, color: 'hover:bg-orange-900/40 text-orange-300 border-orange-800/40' },
    { label: 'Error Alert', event: 'ERROR', icon: XCircle, color: 'hover:bg-red-900/40 text-red-300 border-red-800/40' },
  ];

  return (
    <div className="space-y-8">
      {/* State & Event Telemetry Bar */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className={`p-4 rounded-xl border ${currentStateStyle.border} ${currentStateStyle.bg} flex items-center justify-between`}>
          <div>
            <div className="text-xs uppercase tracking-wider text-dev-text-muted font-bold">Persistent State</div>
            <div className={`text-xl font-bold mt-1 ${currentStateStyle.text}`}>{developerState || 'IDLE'}</div>
          </div>
          <div className={`w-3.5 h-3.5 rounded-full ${currentStateStyle.text === 'text-amber-400' ? 'bg-amber-400 animate-pulse' : 'bg-current animate-ping'}`} />
        </div>

        <div className="p-4 rounded-xl border border-dev-border-light bg-dev-surface-pressed flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-wider text-dev-text-muted font-bold">Active Event</div>
            <div className="text-xl font-bold mt-1 text-dev-text">
              {developerEvent ? developerEvent : <span className="text-dev-text-muted text-sm font-normal">None (Listening on :9999)</span>}
            </div>
          </div>
          <Terminal className="text-dev-text-muted w-5 h-5" />
        </div>
      </div>

      {/* 300-LED Live Strip Preview */}
      <LedStripPreview300 />

      {/* Simulation Controls */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-dev-text">Simulate Developer Activity</h3>
          <span className="text-xs text-dev-text-muted">Click any event to trigger real-time LED visuals</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2.5">
          {quickActions.map(({ label, event, icon: Icon, color }) => (
            <button
              key={event}
              onClick={() => triggerDeveloperEvent(event)}
              className={`p-3 rounded-xl border bg-dev-surface-elevated ${color} flex flex-col items-center justify-center gap-1.5 text-xs font-semibold cursor-pointer transition-all active:scale-95 shadow-sm`}
            >
              <Icon size={16} />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* API Ingestion Info Box */}
      <div className="p-4 rounded-xl border border-dev-border-light bg-dev-surface-pressed/50 text-xs text-dev-text-muted space-y-2">
        <div className="font-bold text-dev-text flex items-center gap-2">
          <Terminal size={14} />
          <span>HTTP Event API (Port 9999)</span>
        </div>
        <p>Trigger events from scripts, IDE plugins, or terminal hooks:</p>
        <code className="block p-2.5 rounded bg-black/40 text-emerald-400 font-mono select-all overflow-x-auto">
          curl -X POST http://localhost:9999/event -H "Content-Type: application/json" -d '{`{"event":"BUILD_STARTED"}`}'
        </code>
      </div>
    </div>
  );
};
