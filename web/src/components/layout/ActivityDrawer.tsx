import React, { useState } from 'react';
import { Terminal, ChevronUp, ChevronDown, Trash2 } from 'lucide-react';

interface ActivityDrawerProps {
  logs: Array<{ time: string; level: string; msg: string }>;
  onClear: () => void;
}

export const ActivityDrawer: React.FC<ActivityDrawerProps> = ({ logs, onClear }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div
      className="border-t transition-all select-none"
      style={{ backgroundColor: 'var(--app-drawer-bg)', borderColor: 'var(--border-subtle)' }}
    >
      {/* Drawer Toggle Bar */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="h-7 px-4 flex items-center justify-between cursor-pointer border-t text-[11px] font-mono-code"
        style={{ backgroundColor: 'var(--bg-surface-base)', borderColor: 'var(--border-subtle)', color: 'var(--text-secondary)' }}
      >
        <div className="flex items-center space-x-2">
          <Terminal className="w-3.5 h-3.5 text-blue-400" />
          <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>System Activity & Protocol Diagnostics</span>
          <span className="px-1.5 py-0.2 bg-blue-500/10 text-blue-400 rounded text-[10px] border border-blue-500/20">
            {logs.length} Events
          </span>
        </div>

        <div className="flex items-center space-x-3">
          {isOpen && (
            <button 
              onClick={(e) => { e.stopPropagation(); onClear(); }}
              className="text-slate-500 hover:text-slate-300 flex items-center space-x-1"
            >
              <Trash2 className="w-3 h-3" />
              <span>Clear</span>
            </button>
          )}
          {isOpen ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronUp className="w-4 h-4 text-slate-400" />}
        </div>
      </div>

      {/* Expanded Logs Drawer Content */}
      {isOpen && (
        <div
          className="p-3 font-mono-code text-[11px] overflow-y-auto space-y-1"
          style={{ height: 'var(--drawer-height)', backgroundColor: 'var(--app-bg)' }}
        >
          {logs.length > 0 ? (
            logs.map((l, i) => (
              <div key={i} className="flex items-center space-x-3 text-slate-300 hover:bg-white/[0.02] px-2 py-0.5 rounded">
                <span className="text-slate-500">{l.time}</span>
                <span className={`px-1.5 py-0.2 rounded font-bold text-[10px] ${
                  l.level === 'ERROR' ? 'bg-rose-500/20 text-rose-400' :
                  l.level === 'WARN' ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'
                }`}>
                  {l.level}
                </span>
                <span className="text-slate-200">{l.msg}</span>
              </div>
            ))
          ) : (
            <div className="text-slate-600 text-center pt-8">No system activity events recorded.</div>
          )}
        </div>
      )}
    </div>
  );
};
