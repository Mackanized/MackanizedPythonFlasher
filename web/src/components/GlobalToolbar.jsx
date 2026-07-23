import React from 'react';
import { 
  Plug, Unplug, BookOpen, AlertOctagon, 
  Search, ToggleLeft, ToggleRight, Flame 
} from 'lucide-react';

export default function GlobalToolbar({ 
  isConnected, onConnect, onRead, onWrite, onEmergencyStop, 
  workshopMode, setWorkshopMode, searchQuery, setSearchQuery 
}) {
  return (
    <div className="h-12 px-4 bg-[#11131C] border-b border-white/[0.04] flex items-center justify-between gap-4 select-none">
      {/* Primary Action Group */}
      <div className="flex items-center space-x-2">
        <button
          onClick={onConnect}
          className={`h-8 px-3.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all shadow-sm ${
            isConnected
              ? 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
              : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-600/20'
          }`}
          title="Connect or Disconnect Hardware Adapter"
        >
          {isConnected ? <Unplug className="w-3.5 h-3.5 text-slate-300" /> : <Plug className="w-3.5 h-3.5" />}
          <span>{isConnected ? 'Disconnect' : 'Connect Hardware'}</span>
        </button>

        <button
          onClick={onRead}
          className="h-8 px-3 rounded-lg text-xs font-medium bg-[#1C202E] hover:bg-[#252A3D] text-slate-200 border border-white/[0.05] flex items-center space-x-1.5 transition-all"
          title="Initiate safety backup read of target ECU flash memory"
        >
          <BookOpen className="w-3.5 h-3.5 text-slate-400" />
          <span>Read ECU</span>
        </button>

        <button
          onClick={onWrite}
          className="h-8 px-3 rounded-lg text-xs font-semibold bg-amber-600/90 hover:bg-amber-500 text-white shadow-sm shadow-amber-600/20 border border-amber-500/30 flex items-center space-x-1.5 transition-all"
          title="Initiate high-consequence ECU flash programming session"
        >
          <Flame className="w-3.5 h-3.5 text-amber-200" />
          <span>Write Flash</span>
        </button>

        <div className="h-4 w-px bg-white/10 mx-1" />

        <button
          onClick={onEmergencyStop}
          className="h-8 px-3 rounded-lg text-xs font-bold bg-rose-600/90 hover:bg-rose-500 text-white shadow-sm shadow-rose-600/20 border border-rose-500/30 flex items-center space-x-1.5 transition-all active:scale-95"
          title="Latch Safety Abort: Terminate active programming and reset ECU"
        >
          <AlertOctagon className="w-3.5 h-3.5" />
          <span>Emergency Stop</span>
        </button>
      </div>

      {/* Search & Workshop Toggle */}
      <div className="flex items-center space-x-3">
        <div className="relative w-64">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search ECU, DTCs, CAN IDs... (Ctrl+F)"
            className="w-full h-8 pl-8 pr-3 bg-[#1A1D29] text-xs text-slate-200 placeholder-slate-500 rounded-lg border border-white/[0.05] focus:outline-none focus:border-blue-500/50 transition-colors"
          />
        </div>

        <button
          onClick={() => setWorkshopMode(!workshopMode)}
          className={`h-8 px-3 rounded-lg text-xs font-medium flex items-center space-x-1.5 border transition-all ${
            workshopMode 
              ? 'bg-blue-600/10 text-blue-400 border-blue-500/30' 
              : 'bg-[#1C202E] text-slate-400 border-white/[0.05] hover:text-slate-200'
          }`}
        >
          {workshopMode ? <ToggleRight className="w-4 h-4 text-blue-400" /> : <ToggleLeft className="w-4 h-4" />}
          <span>Workshop Mode</span>
        </button>
      </div>
    </div>
  );
}
