import React from 'react';
import { 
  Zap, Search, Binary, Activity, 
  Terminal, Settings 
} from 'lucide-react';

export default function NavRail({ activeTab, setActiveTab }) {
  const items = [
    { id: 0, key: 'flash', label: 'ECU Flashing', icon: Zap },
    { id: 1, key: 'diag', label: 'UDS & CAN', icon: Search },
    { id: 2, key: 'memory', label: 'Memory & Hex', icon: Binary },
    { id: 3, key: 'telemetry', label: 'Telemetry', icon: Activity },
    { id: 4, key: 'logs', label: 'Audit Logs', icon: Terminal },
    { id: 5, key: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <nav className="w-44 bg-[#0E1017] border-r border-white/[0.04] p-2 flex flex-col justify-between select-none">
      <div className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full h-9 px-3 rounded-lg text-xs font-semibold flex items-center space-x-2.5 transition-all ${
                isActive
                  ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm shadow-blue-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-slate-500'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="p-3 bg-[#131622] rounded-xl border border-white/[0.04] text-[11px] text-slate-400">
        <div className="font-semibold text-slate-300 mb-1">Station Status</div>
        <div className="flex items-center space-x-1.5 text-emerald-400 font-medium">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
          <span>Engine Ready</span>
        </div>
      </div>
    </nav>
  );
}
