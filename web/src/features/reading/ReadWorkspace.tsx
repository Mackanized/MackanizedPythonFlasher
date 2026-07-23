import React, { useEffect, useMemo, useState } from 'react';
import { EcuIdentityInfo, OperationStatus, getPyWebViewGateway } from '../../services/pywebview/bridge';

interface ReadWorkspaceProps {
  ecu: EcuIdentityInfo | null;
  voltage: number | null;
  isConnected: boolean;
  onNavigateToConnect?: () => void;
}

export const ReadWorkspace: React.FC<ReadWorkspaceProps> = ({
  ecu,
  voltage,
  isConnected,
  onNavigateToConnect,
}) => {
  const [selectedRegion, setSelectedRegion] = useState('full');
  const [operation, setOperation] = useState<OperationStatus | null>(null);
  const [error, setError] = useState('');
  const gateway = getPyWebViewGateway();
  const readRegions = useMemo(() => ecu?.readRegions ?? [], [ecu?.readRegions]);

  useEffect(() => {
    if (readRegions.length && !readRegions.includes(selectedRegion)) {
      setSelectedRegion(readRegions[0]);
    }
  }, [readRegions, selectedRegion]);

  useEffect(() => {
    if (!operation?.active) return;
    const poll = async () => {
      const status = await gateway.getOperationStatus();
      setOperation(status);
      if (status.state === 'failed') setError(status.message || status.details);
    };
    const timer = window.setInterval(poll, 200);
    void poll();
    return () => window.clearInterval(timer);
  }, [gateway, operation?.active]);

  const handleStartRead = async () => {
    if (!isConnected) {
      setError('Connect to the ECU before reading memory.');
      return;
    }
    if (ecu?.supportsRead === false) {
      setError('Reading is not verified for this ECU definition.');
      return;
    }
    setError('');
    try {
      const startResult = await gateway.startFlashRead(selectedRegion);
      if (!startResult.accepted) {
        setError('Read start was rejected. Verify the connection and that no operation is active.');
        return;
      }
      setOperation(await gateway.getOperationStatus());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to start read.');
    }
  };

  const isReading = Boolean(operation?.active && operation.operation === 'read');
  const isVoltageNominal = voltage !== null && voltage >= 12.5;

  return (
    <div
      className="space-y-4 overflow-y-auto h-full select-none text-xs font-sans"
      style={{ padding: 'var(--workspace-padding)', backgroundColor: 'var(--bg-surface-base)', color: 'var(--text-primary)' }}
    >
      <div className="p-3 rounded-sm border space-y-1" style={{ backgroundColor: 'var(--panel-bg)', borderColor: 'var(--panel-border)' }}>
        <h1 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>ECU Flash Memory Reading Workflow</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Read memory through the backend protocol engine. A connected ECU is required.
        </p>
      </div>

      {!isConnected && (
        <div className="p-3 bg-[#1F2129] border border-[#F59E0B]/30 rounded-sm flex items-center justify-between text-xs text-[#F59E0B]">
          <span>Hardware connection required. You must connect to an ECU before reading memory.</span>
          {onNavigateToConnect && (
            <button
              type="button"
              onClick={onNavigateToConnect}
              className="px-3 py-1 bg-[#3B82F6] text-white font-semibold rounded-sm hover:bg-[#2563EB] transition-colors text-xs ml-3 flex-shrink-0"
            >
              Connect to ECU
            </button>
          )}
        </div>
      )}

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-7 p-4 rounded-sm border space-y-4" style={{ backgroundColor: 'var(--panel-bg)', borderColor: 'var(--panel-border)' }}>
          <div className="space-y-2">
            <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider border-b border-[#252B3E] pb-1.5">
              Select Memory Region to Read
            </h2>
            <div className="space-y-2 pt-1">
              {readRegions.map((region) => (
                <button
                  type="button"
                  key={region}
                  onClick={() => setSelectedRegion(region)}
                  disabled={isReading}
                  className={`w-full text-left p-3 rounded-sm border transition-colors ${
                    selectedRegion === region
                      ? 'bg-[#1F2332] border-[#2563EB]'
                      : 'bg-[#181B27] border-[#252B3E] hover:border-[#333B54]'
                  }`}
                >
                  <div className="font-bold text-slate-200">{region}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">Declared by the selected ECU definition.</div>
                </button>
              ))}
            </div>
          </div>

          <div className="pt-2 border-t border-[#252B3E] text-slate-400">
            The backend creates a timestamped binary in the configured application output directory.
          </div>

          {error && <div className="text-rose-400">{error}</div>}
          <button
            onClick={handleStartRead}
            disabled={!isConnected || isReading || ecu?.supportsRead === false || readRegions.length === 0}
            className="w-full h-10 bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold rounded-sm border border-blue-400/30 transition-colors"
          >
            {isReading
              ? 'Reading Flash Memory...'
              : ecu?.supportsRead === false
                ? 'Reading unsupported for this ECU definition'
                : isConnected ? 'Start Flash Memory Read' : 'Connect to ECU before reading'}
          </button>
        </div>

        <div className="col-span-5 p-4 rounded-sm border space-y-4 flex flex-col justify-between" style={{ backgroundColor: 'var(--panel-bg)', borderColor: 'var(--panel-border)' }}>
          <div className="space-y-3">
            <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider border-b border-[#252B3E] pb-1.5">
              Target Controller State
            </h2>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-[#1C202E]">
                <span className="text-slate-400">Connection</span>
                <span className={isConnected ? 'font-bold text-emerald-400' : 'font-bold text-rose-400'}>
                  {isConnected ? (ecu?.isSimulation ? 'Simulator connected' : 'Connected') : 'Disconnected'}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1C202E]">
                <span className="text-slate-400">Target Controller</span>
                <span className="font-bold text-slate-200">{ecu?.name || 'Not identified'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1C202E]">
                <span className="text-slate-400">Supply Voltage</span>
                <span className={`font-mono-code font-bold ${isVoltageNominal ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {voltage === null ? 'Unknown' : `${voltage.toFixed(2)}V`}
                </span>
              </div>
            </div>
          </div>

          {isReading && operation && (
            <div className="p-3 bg-[#181B27] rounded-sm border border-[#2563EB] space-y-2">
              <div className="flex justify-between font-mono-code text-xs font-bold text-blue-400">
                <span>{operation.phase}</span>
                <span>{operation.percent}%</span>
              </div>
              <div className="text-[11px] text-slate-400">{operation.details}</div>
              <div className="w-full h-2 bg-[#0D0E12] rounded-full overflow-hidden">
                <div className="h-full bg-[#2563EB] transition-all duration-200" style={{ width: `${operation.percent}%` }} />
              </div>
            </div>
          )}

          {operation && !operation.active && operation.state === 'completed' && operation.operation === 'read' && (
            <div className="p-3 bg-[#142E23] border border-[#165B3E] rounded-sm space-y-1">
              <div className="font-bold text-emerald-400">Read Operation Completed</div>
              <div className="text-[11px] text-emerald-200">{operation.message}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
