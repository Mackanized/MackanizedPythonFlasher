import React from 'react';

export default function MemoryWorkspace() {
  return (
    <div
      className="h-full"
      style={{ padding: 'var(--workspace-padding)', backgroundColor: 'var(--bg-surface-base)', color: 'var(--text-primary)' }}
    >
      <div className="py-6 border-b border-white/[0.06] space-y-3">
        <h2 className="text-sm font-bold text-slate-200">Memory inspector</h2>
        <p className="text-sm text-slate-300">No memory artifact is loaded.</p>
        <p className="text-xs text-slate-500">
          Complete a read and load its verified artifact before bytes, addresses, or fingerprints can be displayed.
          This workspace never generates placeholder ECU contents.
        </p>
      </div>
    </div>
  );
}
