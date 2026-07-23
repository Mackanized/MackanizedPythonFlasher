import React from 'react';
import { TelemetryPayload } from '../services/pywebview/bridge';

interface TelemetryWorkspaceProps {
  telemetryData: TelemetryPayload | null;
}

export default function TelemetryWorkspace({ telemetryData }: TelemetryWorkspaceProps) {
  const voltage = telemetryData?.voltage;
  const metrics = [
    { title: 'Battery voltage', value: voltage == null ? 'Unknown' : `${voltage.toFixed(2)} V`, status: voltage == null ? 'No measurement source' : telemetryData?.voltage_status, color: voltage == null ? 'text-slate-400' : 'text-emerald-400' },
    { title: 'CAN bus load', value: telemetryData?.can_bus_load == null ? 'Unknown' : `${telemetryData.can_bus_load} %`, status: telemetryData?.source ?? 'No adapter counters', color: 'text-blue-400' },
    { title: 'CPU utilization', value: telemetryData?.cpu_usage_pct == null ? 'Unknown' : `${telemetryData.cpu_usage_pct} %`, status: 'Measured host process', color: 'text-slate-200' },
    { title: 'RAM high-water mark', value: telemetryData?.memory_usage_mb == null ? 'Unknown' : `${Math.round(telemetryData.memory_usage_mb)} MB`, status: 'Measured process usage', color: 'text-amber-400' },
  ];

  return (
    <div
      className="space-y-4 overflow-y-auto h-full flex flex-col justify-between select-none"
      style={{ padding: 'var(--workspace-padding)', backgroundColor: 'var(--bg-surface-base)', color: 'var(--text-primary)' }}
    >
      <div className="grid grid-cols-4 gap-6 border-b border-white/[0.06] pb-4">
        {metrics.map((m) => (
          <div key={m.title} className="space-y-1">
            <div className="text-xs text-slate-400 font-semibold">{m.title}</div>
            <div className={`text-2xl font-mono-code font-bold ${m.color}`}>
              {m.value}
            </div>
            <div className="text-[10px] text-slate-500 font-medium">{m.status}</div>
          </div>
        ))}
      </div>

      <div className="py-4 flex-1 flex flex-col justify-between space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-300">Real-time CAN bus load and frame frequency</h3>
          <span className="text-xs font-mono-code text-slate-400">Measured every 500 ms</span>
        </div>

        <div className="h-56 w-full bg-[#0E1017] border border-white/[0.04] relative overflow-hidden flex items-center justify-center p-4">
          <div className="text-center text-slate-400 text-xs space-y-2">
            <div>TX: {telemetryData?.tx_fps == null ? 'Unknown' : `${telemetryData.tx_fps} fps`}</div>
            <div>RX: {telemetryData?.rx_fps == null ? 'Unknown' : `${telemetryData.rx_fps} fps`}</div>
            <div className="text-slate-600">Historical charting is unavailable until measured samples are persisted.</div>
          </div>
        </div>
      </div>
    </div>
  );
}
