import React from 'react';
import { 
  Zap, Plug, Search, Activity, 
  Binary, Clock, Settings, AlertOctagon 
} from 'lucide-react';

export type WorkspaceTab = 
  | 'flash'
  | 'read'
  | 'connect'
  | 'diagnostics'
  | 'telemetry'
  | 'memory'
  | 'recovery'
  | 'history'
  | 'settings';

interface NavRailProps {
  activeTab: WorkspaceTab;
  setActiveTab: (tab: WorkspaceTab) => void;
  isRecoveryRequired?: boolean;
}

export const NavRail: React.FC<NavRailProps> = ({
  activeTab,
  setActiveTab,
  isRecoveryRequired = false,
}) => {
  const items: { id: WorkspaceTab; label: string; icon: React.ElementType }[] = [
    { id: 'flash', label: 'Flash ECU', icon: Zap },
    { id: 'read', label: 'Read ECU', icon: Zap },
    { id: 'connect', label: 'Connect', icon: Plug },
    { id: 'diagnostics', label: 'Diagnostics', icon: Search },
    { id: 'telemetry', label: 'Live Data', icon: Activity },
    { id: 'memory', label: 'Memory Hex', icon: Binary },
    { id: 'recovery', label: 'Recovery', icon: AlertOctagon },
    { id: 'history', label: 'History', icon: Clock },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  if (isRecoveryRequired) {
    return (
      <nav className="w-32 bg-[#0D0E12] border-r border-[#7F1D1D] p-1.5 flex flex-col justify-between select-none text-[11px]">
        <div className="p-2 bg-[#350F0F] border border-[#7F1D1D] rounded-sm space-y-1">
          <AlertOctagon className="w-5 h-5 text-rose-400 mx-auto" />
          <div className="text-center font-bold text-[9px] text-rose-300 uppercase">
            RECOVERY
          </div>
        </div>
      </nav>
    );
  }

  return (
    <nav
      className="w-32 border-r p-1 flex flex-col justify-between select-none font-sans"
      style={{ backgroundColor: 'var(--app-nav-bg)', borderColor: 'var(--border-subtle)' }}
    >
      <div className="space-y-0.5">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full h-7 px-2 rounded-sm text-[11px] font-semibold flex items-center space-x-2 transition-colors ${
                isActive
                  ? 'font-bold'
                  : 'hover:text-slate-200'
              }`}
              style={{
                backgroundColor: isActive ? 'var(--selected-bg)' : 'transparent',
                color: isActive ? 'var(--selected-text)' : 'var(--text-secondary)',
              }}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-slate-500'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      <div
        className="p-1.5 rounded-sm border text-[10px] font-mono-code"
        style={{ backgroundColor: 'var(--panel-bg)', borderColor: 'var(--panel-border)', color: 'var(--text-secondary)' }}
      >
        <div className="text-[8px] uppercase font-bold" style={{ color: 'var(--text-muted)' }}>Python Core</div>
        <div className="flex items-center space-x-1 text-[#4ADE80] font-semibold mt-0.5">
          <div className="w-1.5 h-1.5 rounded-full bg-[#4ADE80]" />
          <span>Active</span>
        </div>
      </div>
    </nav>
  );
};
