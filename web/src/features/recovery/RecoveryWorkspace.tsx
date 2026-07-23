import React, { useEffect, useState } from 'react';
import {
  EcuIdentityInfo,
  OperationStatus,
  getPyWebViewGateway,
} from '../../services/pywebview/bridge';

interface RecoveryWorkspaceProps {
  ecu: EcuIdentityInfo | null;
  voltage: number | null;
  isConnected: boolean;
}

export const RecoveryWorkspace: React.FC<RecoveryWorkspaceProps> = ({ ecu, voltage, isConnected }) => {
  const [backupVerified, setBackupVerified] = useState(false);
  const [operation, setOperation] = useState<OperationStatus | null>(null);
  const [message, setMessage] = useState('');
  const gateway = getPyWebViewGateway();
  const isT8 = (ecu?.name || '').toLowerCase() === 'trionic 8';
  const isVoltageSafe = voltage !== null && voltage >= 12.5;
  const canPrepare = isConnected && isT8 && ecu?.supportsRecovery !== false && isVoltageSafe && backupVerified;

  useEffect(() => {
    if (!operation?.active) return;
    const timer = window.setInterval(async () => {
      const status = await gateway.getOperationStatus();
      setOperation(status);
      setMessage(status.message || status.details || '');
      if (!status.active) window.clearInterval(timer);
    }, 200);
    return () => window.clearInterval(timer);
  }, [gateway, operation?.active]);

  const startRecovery = async () => {
    setMessage('');
    try {
      const result = await gateway.startRecoveryFlash(true, backupVerified);
      if (!result.accepted) {
        setMessage('Recovery preparation was rejected. Verify T8 selection, ECU connection, voltage, backup confirmation, and active operation state.');
        return;
      }
      const status = await gateway.getOperationStatus();
      setOperation(status);
      setMessage(status.details || 'T8 recovery preparation started.');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Unable to start recovery.');
    }
  };

  return (
    <div
      className="h-full text-xs overflow-y-auto"
      style={{
        padding: 'var(--workspace-padding)',
        backgroundColor: 'var(--bg-surface-base)',
        color: 'var(--text-primary)',
      }}
    >
      <div className="max-w-2xl mx-auto mt-16 space-y-5">
        <div className="border-b pb-3" style={{ borderColor: 'var(--border-subtle)' }}>
          <h1 className="text-sm font-bold text-amber-400">T8 recovery flash preparation</h1>
          <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>
            This flow enters the Trionic 8 recovery session and uploads/starts the recovery programming loader.
            It does not erase memory or transfer a firmware image.
          </p>
        </div>

        <div className="grid grid-cols-[160px_1fr] gap-y-2 py-2">
          <span style={{ color: 'var(--text-secondary)' }}>Target controller</span>
          <span className="font-semibold">{ecu?.name || 'Not identified'}</span>
          <span style={{ color: 'var(--text-secondary)' }}>Recovery capability</span>
          <span className={ecu?.supportsRecovery !== false ? 'text-emerald-400 font-semibold' : 'text-amber-400 font-semibold'}>
            {ecu?.supportsRecovery !== false ? 'Declared by ECU definition' : 'Not released'}
          </span>
          <span style={{ color: 'var(--text-secondary)' }}>Connection</span>
          <span className={isConnected ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
          <span style={{ color: 'var(--text-secondary)' }}>Supply voltage</span>
          <span className={isVoltageSafe ? 'text-emerald-400 font-semibold' : 'text-amber-400 font-semibold'}>
            {voltage === null ? 'Unknown' : `${voltage.toFixed(2)} V`}
          </span>
        </div>

        {!isT8 && (
          <div className="text-amber-400">
            Dedicated recovery-loader preparation is currently exposed only for Trionic 8.
          </div>
        )}

        <label className="flex items-start gap-3 p-3 border cursor-pointer" style={{ borderColor: 'var(--border-subtle)' }}>
          <input
            type="checkbox"
            checked={backupVerified}
            onChange={(event) => setBackupVerified(event.target.checked)}
            className="mt-0.5"
          />
          <span>
            <span className="block font-semibold">Backup verified</span>
            <span className="block" style={{ color: 'var(--text-secondary)' }}>
              I have a readable backup and a stable bench recovery setup before preparing the recovery loader.
            </span>
          </span>
        </label>

        <button
          type="button"
          onClick={startRecovery}
          disabled={!canPrepare}
          className="w-full h-9 bg-amber-600 hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed text-black font-bold rounded-sm transition-colors"
        >
          Prepare T8 recovery session and loader
        </button>

        {operation && (
          <div>
            {operation.operation}: {operation.phase} — {operation.percent}%
          </div>
        )}
        {message && <div style={{ color: 'var(--text-secondary)' }}>{message}</div>}
      </div>
    </div>
  );
};
