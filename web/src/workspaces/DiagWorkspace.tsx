import React, { useState } from 'react';
import { Play, Trash2 } from 'lucide-react';
import { getPyWebViewGateway } from '../services/pywebview/bridge';

interface DiagWorkspaceProps {
  isConnected: boolean;
  isSimulation: boolean;
}

interface DtcRow {
  code: string;
  description: string;
  status: string;
  severity: string;
}

export default function DiagWorkspace({ isConnected, isSimulation }: DiagWorkspaceProps) {
  const [dtcs, setDtcs] = useState<DtcRow[]>([]);
  const [error, setError] = useState('');
  const gateway = getPyWebViewGateway();

  const readDtcs = async () => {
    setError('');
    try {
      setDtcs(await gateway.readDtcs());
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'DTC read failed.');
    }
  };

  const clearDtcs = async () => {
    setError('');
    if (await gateway.clearDtcs()) setDtcs([]);
    else setError('DTC clear is unavailable or was rejected.');
  };

  return (
    <div
      className="h-full text-xs"
      style={{ padding: 'var(--workspace-padding)', backgroundColor: 'var(--bg-surface-base)', color: 'var(--text-secondary)' }}
    >
      <div className="max-w-3xl mx-auto space-y-4">
        <div className="py-3 border-b border-white/[0.06] space-y-1">
          <h1 className="text-sm font-bold text-slate-100">Diagnostic Trouble Codes</h1>
          <p className="text-slate-400">
            {isSimulation
              ? 'Simulation mode: returned faults belong only to the virtual ECU.'
              : 'Hardware DTC services remain disabled until a trace-backed diagnostic strategy is implemented.'}
          </p>
        </div>

        <div className="py-3 space-y-3">
          <div className="flex items-center justify-between">
            <div className="font-bold text-slate-200">Fault memory</div>
            <div className="flex gap-2">
              <button disabled={!isConnected || !isSimulation} onClick={readDtcs} className="h-8 px-3 bg-blue-700 disabled:opacity-40 flex items-center gap-1 rounded-sm">
                <Play className="w-3 h-3" /> Read DTCs
              </button>
              <button disabled={!isConnected || !isSimulation} onClick={clearDtcs} className="h-8 px-3 bg-rose-800 disabled:opacity-40 flex items-center gap-1 rounded-sm">
                <Trash2 className="w-3 h-3" /> Clear DTCs
              </button>
            </div>
          </div>

          {error && <div className="text-rose-400">{error}</div>}
          {!isConnected && <div className="text-amber-400">Connect to an ECU before using diagnostics.</div>}
          {isConnected && !isSimulation && <div className="text-amber-400">DTC actions are not supported for physical hardware.</div>}

          {dtcs.length ? (
            <table className="w-full text-left font-mono-code">
              <thead><tr className="border-b border-white/[0.08]"><th className="p-2">Code</th><th>Description</th><th>Status</th></tr></thead>
              <tbody>
                {dtcs.map((dtc) => (
                  <tr key={dtc.code} className="border-b border-white/[0.04]">
                    <td className="p-2 text-amber-400 font-bold">{dtc.code}</td>
                    <td>{dtc.description}</td>
                    <td>{dtc.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="py-8 text-center text-slate-500">
              No backend DTC result loaded.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
