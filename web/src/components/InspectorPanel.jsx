import React from 'react';
import { SlidersHorizontal, Info } from 'lucide-react';

export default function InspectorPanel({ ecuData }) {
  const props = [
    { label: 'Target ECU', value: ecuData?.name || 'Motronic ME9.6.1' },
    { label: 'Vehicle Platform', value: ecuData?.vehicle || 'Saab / Opel 2.8T V6' },
    { label: 'Hardware No.', value: ecuData?.hw || '0261208961' },
    { label: 'Software No.', value: ecuData?.sw || '1037383491' },
    { label: 'Microcontroller', value: ecuData?.mcu || 'MPC564 / Flash 2MB' },
    { label: 'Protocol Stack', value: ecuData?.proto || 'UDS over CAN (ISO 15765)' },
    { label: 'Security Algo', value: ecuData?.sec || 'Bosch Key Algo (0x27)' },
    { label: 'Flash Memory', value: ecuData?.flash || '2048 KB (2 MB)' },
    { label: 'EEPROM Emulation', value: ecuData?.eep || '95160 (2 KB)' },
  ];

  return (
    <aside className="w-64 bg-[#0E1017] border-l border-white/[0.04] p-3 flex flex-col select-none overflow-y-auto">
      <div className="flex items-center justify-between pb-3 mb-2 border-b border-white/[0.04]">
        <div className="flex items-center space-x-2">
          <SlidersHorizontal className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
            Property Inspector
          </span>
        </div>
        <Info className="w-3.5 h-3.5 text-slate-500 hover:text-slate-300 cursor-pointer" />
      </div>

      <div className="space-y-2">
        {props.map((item, idx) => (
          <div key={idx} className="p-2.5 rounded-lg bg-[#141724] border border-white/[0.03] hover:border-white/[0.08] transition-all">
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">
              {item.label}
            </div>
            <div className="text-xs font-mono-code font-semibold text-slate-200 mt-0.5 truncate" title={item.value}>
              {item.value}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
