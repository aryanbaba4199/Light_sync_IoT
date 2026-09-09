import React, { useState, useEffect } from 'react';
import { Home, Palette, Zap, Settings as SettingsIcon } from 'lucide-react';
import { useLightingStore } from './store/lightingStore';

import { DashboardScreen } from './screens/DashboardScreen';
import { ExperiencesScreen } from './screens/ExperiencesScreen';
import { DevicesScreen } from './screens/DevicesScreen';
import { SettingsScreen } from './screens/SettingsScreen';

type Tab = 'home' | 'experiences' | 'devices' | 'settings';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('home');
  const initialize = useLightingStore((state) => state.initialize);
  const engineConnected = useLightingStore((state) => state.engineConnected);

  useEffect(() => {
    initialize();
  }, [initialize]);

  const renderContent = () => {
    switch (activeTab) {
      case 'home': return <DashboardScreen />;
      case 'experiences': return <ExperiencesScreen />;
      case 'devices': return <DevicesScreen />;
      case 'settings': return <SettingsScreen />;
    }
  };

  const NavItem = ({ id, icon: Icon, label }: { id: Tab, icon: any, label: string }) => {
    const isActive = activeTab === id;
    return (
      <button
        onClick={() => setActiveTab(id)}
        className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer transition-all duration-200 border-none font-medium text-[15px]
          ${isActive 
            ? 'bg-dev-surface-pressed text-dev-primary' 
            : 'bg-transparent text-dev-text-secondary hover:bg-dev-surface-elevated hover:text-dev-text'
          }`}
      >
        <Icon size={20} />
        <span>{label}</span>
      </button>
    );
  };

  return (
    <div className="flex flex-col h-screen bg-dev-bg text-dev-text">
      {/* Title Bar drag region for frameless Mac window */}
      <div className="title-bar shrink-0"></div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <nav className="w-60 bg-dev-surface border-r border-dev-border flex flex-col shrink-0">
          <div className="flex items-center gap-2 p-6 text-dev-text">
            <Zap className="text-dev-primary" size={24} />
            <h3 className="font-semibold text-lg">DevLights</h3>
          </div>

          <div className="flex-1 px-3 flex flex-col gap-1">
            <NavItem id="home" icon={Home} label="Home" />
            <NavItem id="experiences" icon={Palette} label="Experiences" />
            <NavItem id="devices" icon={Zap} label="Devices" />
            <NavItem id="settings" icon={SettingsIcon} label="Settings" />
          </div>
          
          <div className="p-4 border-t border-dev-border">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${engineConnected ? 'bg-dev-success' : 'bg-dev-error animate-pulse'}`}></div>
              <span className="caption">{engineConnected ? 'Engine Online' : 'Engine Disconnected'}</span>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto relative">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

export default App;
