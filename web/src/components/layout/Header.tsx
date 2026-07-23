import React from 'react';
import { TelemetryPayload, EcuIdentityInfo } from '../../services/pywebview/bridge';

interface HeaderProps {
  ecus: Array<{ id: string; name: string }>;
  activeEcuId: string;
  onSelectEcu: (ecuId: string) => void;
  ecuInfo: EcuIdentityInfo | null;
  securityState: string;
  isConnected: boolean;
  telemetry: TelemetryPayload | null;
}

export const Header: React.FC<HeaderProps> = ({
  ecus,
  activeEcuId,
  onSelectEcu,
  ecuInfo,
  securityState: _securityState,
  isConnected,
  telemetry,
}) => {
  const voltage = telemetry?.voltage ?? null;
  const isVoltageNominal = voltage !== null && voltage >= 12.5;

  return (
    <header
      className="px-3 border-b flex items-center justify-between select-none font-sans text-xs"
      style={{
        height: 'var(--header-height)',
        backgroundColor: 'var(--app-header-bg)',
        borderColor: 'var(--border-subtle)',
        color: 'var(--text-secondary)',
      }}
    >
      {/* Brand & Controller Selection */}
      <div className="flex items-center space-x-3">
        <span className="font-bold tracking-wide text-xs" style={{ color: 'var(--text-primary)' }}>Mackanized flasher</span>
        <span className="font-normal" style={{ color: 'var(--text-muted)' }}>|</span>
        
        {/* ECU Select */}
        <div className="flex items-center space-x-1.5 text-xs">
          <span className="font-normal" style={{ color: 'var(--text-secondary)' }}>Target:</span>
          <select
            value={activeEcuId}
            onChange={(e) => onSelectEcu(e.target.value)}
            className="bg-transparent font-semibold text-xs focus:outline-none cursor-pointer border-b pb-0.5"
            style={{ color: 'var(--text-primary)', borderColor: 'var(--border-strong)' }}
          >
            {ecus.map((e) => (
              <option key={e.id} value={e.id} style={{ backgroundColor: 'var(--panel-bg)', color: 'var(--text-primary)' }}>
                {e.name}
              </option>
            ))}
          </select>
        </div>

        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          {ecuInfo?.vehicle || 'Controller not identified'}
        </span>
      </div>

      {/* Un-boxed Plain Text Status Metrics */}
      <div className="flex items-center space-x-4 text-xs">
        {/* Voltage */}
        <div className="flex items-center space-x-1 font-mono-code text-[11px]">
          <span className="font-sans" style={{ color: 'var(--text-secondary)' }}>Voltage:</span>
          <span className={`font-bold ${isVoltageNominal ? 'text-[#10B981]' : 'text-[#F59E0B]'}`}>
            {voltage === null ? 'Unknown' : `${voltage.toFixed(2)} V`}
          </span>
        </div>

        {/* Connection State */}
        <div className="flex items-center space-x-1.5 text-[11px]">
          <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-[#10B981]' : 'bg-slate-500'}`} />
          <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
            {isConnected ? 'Hardware Connected' : 'Hardware Disconnected'}
          </span>
        </div>
      </div>
    </header>
  );
};
