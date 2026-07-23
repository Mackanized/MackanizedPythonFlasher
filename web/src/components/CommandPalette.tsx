import React, { useState, useEffect } from 'react';
import { Search, X } from 'lucide-react';
import { globalCommandRegistry, DesktopCommand } from '../services/commands/commandRegistry';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [commands, setCommands] = useState<DesktopCommand[]>(globalCommandRegistry.getAll());

  useEffect(() => {
    return globalCommandRegistry.subscribe(() => {
      setCommands(globalCommandRegistry.getAll());
    });
  }, []);

  if (!isOpen) return null;

  const filtered = commands.filter(
    (c) =>
      c.title.toLowerCase().includes(query.toLowerCase()) ||
      c.description.toLowerCase().includes(query.toLowerCase()) ||
      c.category.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-20 select-none">
      <div className="w-full max-w-xl bg-[#121420] border border-white/[0.1] rounded-xl shadow-2xl overflow-hidden font-sans">
        {/* Search Header */}
        <div className="p-3 border-b border-white/[0.06] flex items-center space-x-3">
          <Search className="w-4 h-4 text-blue-400" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or search actions (e.g. Open, Flash, Settings)..."
            className="flex-1 bg-transparent text-xs text-slate-100 placeholder-slate-500 focus:outline-none"
          />
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filtered.length > 0 ? (
            filtered.map((cmd) => (
              <div
                key={cmd.id}
                onClick={() => {
                  cmd.action();
                  onClose();
                }}
                className="p-2.5 rounded-lg hover:bg-blue-600/15 cursor-pointer flex items-center justify-between group transition-colors"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2 text-xs font-bold text-slate-200 group-hover:text-blue-400">
                    <span>{cmd.title}</span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-white/[0.04] text-slate-400 uppercase font-mono-code">
                      {cmd.category}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400">{cmd.description}</div>
                </div>

                {cmd.shortcut && (
                  <span className="px-2 py-0.5 rounded bg-[#0A0B10] border border-white/[0.06] text-[10px] font-mono-code text-slate-400">
                    {cmd.shortcut}
                  </span>
                )}
              </div>
            ))
          ) : (
            <div className="p-6 text-center text-xs text-slate-500 font-mono-code">
              No matching desktop commands found.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
