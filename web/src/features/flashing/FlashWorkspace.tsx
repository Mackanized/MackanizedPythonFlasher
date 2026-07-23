import React, { useEffect, useMemo, useState } from 'react';
import {
  EcuIdentityInfo,
  FlashProgressPayload,
  OperationStatus,
  getPyWebViewGateway,
} from '../../services/pywebview/bridge';
import { globalOperationMachine, OperationContext } from '../../state/operationMachine';
import { PreflightReview } from './PreflightReview';
import { ActiveOperationView } from './ActiveOperationView';

interface FlashWorkspaceProps {
  ecu: EcuIdentityInfo | null;
  voltage: number | null;
  isConnected: boolean;
  onNavigateToConnect?: () => void;
}

export const FlashWorkspace: React.FC<FlashWorkspaceProps> = ({
  ecu,
  voltage,
  isConnected,
  onNavigateToConnect,
}) => {
  const [fsmContext, setFsmContext] = useState<OperationContext>(globalOperationMachine.getContext());
  const [showPreflight, setShowPreflight] = useState(false);
  const [operation, setOperation] = useState<OperationStatus | null>(null);
  const [error, setError] = useState('');
  const gateway = getPyWebViewGateway();
  const writeRegions = useMemo(() => ecu?.writeRegions ?? [], [ecu?.writeRegions]);

  useEffect(() => {
    if (writeRegions.length && !writeRegions.includes(fsmContext.selectedRegion)) {
      globalOperationMachine.selectRegion(writeRegions[0]);
    }
  }, [writeRegions, fsmContext.selectedRegion]);

  useEffect(() => globalOperationMachine.subscribe((_state, ctx) => setFsmContext(ctx)), []);

  useEffect(() => {
    if (!operation?.active) return;
    const poll = async () => {
      const status = await gateway.getOperationStatus();
      setOperation(status);
      if (status.state === 'failed' || status.state === 'recovery_required') {
        setError(status.message || status.details);
      }
    };
    const timer = window.setInterval(poll, 200);
    void poll();
    return () => window.clearInterval(timer);
  }, [gateway, operation?.active]);

  const handleSelectFile = async () => {
    setError('');
    const res = await gateway.selectCalibrationFile(fsmContext.selectedRegion);
    if (res.isValid && res.path) {
      globalOperationMachine.selectFile(res.path);
      if (res.suggestedRegion && writeRegions.includes(res.suggestedRegion)) {
        globalOperationMachine.selectRegion(res.suggestedRegion);
      }
    }
  };

  const handleConfirmWrite = async (backupVerified: boolean) => {
    if (!isConnected) {
      setError('Connect to the ECU before flashing.');
      setShowPreflight(false);
      return;
    }
    if (!fsmContext.selectedFilePath) {
      setError('Select a firmware file before flashing.');
      setShowPreflight(false);
      return;
    }
    const startResult = await gateway.startFlashWrite(
      fsmContext.selectedFilePath,
      fsmContext.selectedRegion,
      true,
      backupVerified,
    );
    setShowPreflight(false);
    if (!startResult.accepted) {
      setError('Flash start was rejected. Verify the ECU connection and that no operation is active.');
      return;
    }
    setError('');
    setOperation(await gateway.getOperationStatus());
  };

  const handleAbort = async () => {
    await gateway.emergencyStop();
    setOperation(await gateway.getOperationStatus());
  };

  if (showPreflight) {
    return (
      <div
        className="h-full flex items-center justify-center"
        style={{ padding: 'var(--workspace-padding)', backgroundColor: 'var(--bg-surface-base)' }}
      >
        <PreflightReview
          ecu={ecu}
          selectedFile={fsmContext.selectedFilePath}
          voltage={voltage}
          region={fsmContext.selectedRegion}
          isConnected={isConnected}
          onConfirmWrite={handleConfirmWrite}
          onCancel={() => setShowPreflight(false)}
        />
      </div>
    );
  }

  if (operation?.active && operation.operation === 'write') {
    const progress: FlashProgressPayload = {
      phase: operation.phase,
      percent: operation.percent,
      currentAddress: operation.details,
      blockIndex: 0,
      totalBlocks: 0,
      bytesTransferred: 0,
      transferRateKbps: operation.speedKbps,
      etaSeconds: 0,
    };
    return (
      <ActiveOperationView
        operationName={ecu?.isSimulation ? 'Programming simulated ECU memory' : 'Programming ECU memory'}
        progress={progress}
        onAbort={handleAbort}
      />
    );
  }

  return (
    <div
      className="h-full flex flex-col justify-between select-none font-sans text-xs"
      style={{ padding: 'var(--workspace-padding)', backgroundColor: 'var(--bg-surface-base)', color: 'var(--text-primary)' }}
    >
      <div className="max-w-2xl mx-auto w-full space-y-6 my-auto">
        <div className="space-y-1">
          <h1 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            {!fsmContext.selectedFilePath ? 'Select firmware file' : 'Firmware file selected'}
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            {ecu?.supportsWrite === false
              ? 'Physical programming is disabled because this ECU definition has no verified programming/checksum strategy.'
              : !fsmContext.selectedFilePath
                ? 'Choose a binary file for the connected controller. The backend validates it before writing.'
                : 'Review the selected target and safety conditions before starting the backend flash operation.'}
          </p>
        </div>

        {!isConnected && (
          <div className="p-3 bg-[#1F2129] border border-[#F59E0B]/30 rounded-sm flex items-center justify-between text-xs text-[#F59E0B]">
            <span>Hardware connection required. You must connect to an ECU before flashing.</span>
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

        <button
          type="button"
          onClick={handleSelectFile}
          className={`w-full p-8 border border-dashed rounded-sm transition-colors cursor-pointer text-center space-y-2 ${
            fsmContext.selectedFilePath
              ? 'bg-[#1B1C22] border-[#10B981]/50'
              : 'bg-[#1B1C22] border-[#2E313D] hover:border-slate-400'
          }`}
        >
          <div className="text-sm font-semibold text-[#E2E8F0] break-all px-4 max-w-full overflow-hidden">
            {fsmContext.selectedFilePath || 'Select firmware binary file'}
          </div>
          <div className="text-xs text-slate-500">Native file selection; validation occurs before transfer</div>
        </button>

        {writeRegions.length > 0 && (
          <label className="block space-y-1 text-slate-400">
            <span>Target region declared by ECU definition</span>
            <select
              value={fsmContext.selectedRegion}
              onChange={(event) => globalOperationMachine.selectRegion(event.target.value)}
              className="w-full h-9 px-2 bg-[#1B1C22] border border-[#2E313D] text-slate-200"
            >
              {writeRegions.map((region) => <option key={region} value={region}>{region}</option>)}
            </select>
          </label>
        )}

        {fsmContext.selectedFilePath && (
          <div className="py-2 border-t border-b border-[#22242D] space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">Target controller</span>
              <span className="font-semibold text-slate-200">{ecu?.name || 'Not identified'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Connection</span>
              <span className={isConnected ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                {isConnected ? (ecu?.isSimulation ? 'Connected — simulator' : 'Connected') : 'Disconnected'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Validation</span>
              <span className="text-slate-300">Pending backend pre-write checks</span>
            </div>
          </div>
        )}

        {error && <div className="text-rose-400">{error}</div>}
        {operation && !operation.active && operation.state === 'completed' && (
          <div className="text-emerald-400">{operation.message || 'Flash operation completed successfully.'}</div>
        )}

        {!fsmContext.selectedFilePath ? (
          <button
            onClick={handleSelectFile}
            className="w-full h-9 bg-[#2A2D38] hover:bg-[#323644] text-[#E2E8F0] font-semibold rounded-sm border border-[#333646] transition-colors"
          >
            Select firmware file...
          </button>
        ) : (
          <button
            onClick={() => setShowPreflight(true)}
            disabled={!isConnected || ecu?.supportsWrite === false || writeRegions.length === 0}
            className="w-full h-9 bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold rounded-sm transition-colors"
          >
            {ecu?.supportsWrite === false
              ? 'Programming unsupported for this ECU definition'
              : isConnected ? 'Review pre-flight checklist and write flash' : 'Connect to ECU before flashing'}
          </button>
        )}
      </div>
    </div>
  );
};
