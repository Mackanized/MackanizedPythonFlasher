import React, { useState } from 'react';
import { Download } from 'lucide-react';

interface LogRow {
  time: string;
  level: string;
  msg: string;
}

interface LogsWorkspaceProps {
  logs?: LogRow[];
}

export default function LogsWorkspace({ logs = [] }: LogsWorkspaceProps) {
  const [levelFilter, setLevelFilter] = useState('ALL');

  const filteredLogs = levelFilter === 'ALL' ? logs : logs.filter((l) => l.level === levelFilter);

  return (
    <div
      className="space-y-4 overflow-y-auto h-full flex flex-col justify-between select-none"
      style={{ padding: 'var(--workspace-padding)', backgroundColor: 'var(--bg-surface-base)', color: 'var(--text-primary)' }}
    >
      <div className="py-3.5 border-b border-white/[0.06] flex items-center justify-between">
        <h2 className="text-sm font-bold text-slate-200">
          Audit logs and protocol diagnostics trace
        </h2>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 bg-[#1A1D29] px-2.5 py-1 rounded-sm border border-white/[0.06] text-xs">
            <select
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="ALL">All Severities</option>
              <option value="INFO">INFO</option>
              <option value="WARN">WARN</option>
              <option value="TRACE">TRACE</option>
            </select>
          </div>

          <button className="h-8 px-3 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-sm flex items-center space-x-1.5 transition-all">
            <Download className="w-3.5 h-3.5" />
            <span>Export Log</span>
          </button>
        </div>
      </div>

      <div
        className="p-4 border flex-1 font-mono-code text-xs overflow-y-auto space-y-1.5"
        style={{ backgroundColor: 'var(--app-bg)', borderColor: 'var(--border-subtle)' }}
      >
        {filteredLogs.map((log, idx) => (
          <div key={`${log.time}-${idx}`} className="grid grid-cols-[90px_52px_1fr] gap-3 hover:bg-white/[0.02] p-1">
            <span className="text-slate-500">{log.time}</span>
            <span className={`text-[10px] font-bold ${
              log.level === 'INFO' ? 'bg-blue-500/20 text-blue-400' :
              log.level === 'WARN' ? 'bg-amber-500/20 text-amber-400' :
              log.level === 'TRACE' ? 'bg-purple-500/20 text-purple-400' : 'bg-slate-700 text-slate-300'
            }`}>
              {log.level}
            </span>
            <span className="text-slate-200">{log.msg}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
