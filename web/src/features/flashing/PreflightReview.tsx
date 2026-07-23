import React, { useState } from 'react';
import { EcuIdentityInfo } from '../../services/pywebview/bridge';

interface PreflightReviewProps {
  ecu: EcuIdentityInfo | null;
  selectedFile: string | null;
  voltage: number | null;
  region: string;
  isConnected: boolean;
  onConfirmWrite: (backupVerified: boolean) => void;
  onCancel: () => void;
}

export const PreflightReview: React.FC<PreflightReviewProps> = ({
  ecu,
  selectedFile,
  voltage,
  region,
  isConnected,
  onConfirmWrite,
  onCancel,
}) => {
  const [backupVerified, setBackupVerified] = useState(false);
  const isVoltageSafe = voltage !== null && voltage >= 12.5;
  const canWrite = isConnected && isVoltageSafe && Boolean(selectedFile) && backupVerified && ecu?.supportsWrite !== false;

  const checks = [
    { label: 'Connection', value: isConnected ? (ecu?.isSimulation ? 'Connected — simulator' : 'Connected') : 'Disconnected' },
    { label: 'Target vehicle platform', value: ecu?.vehicle || 'Not identified' },
    { label: 'Target controller', value: ecu?.name || 'Not identified' },
    { label: 'Hardware part number', value: ecu?.hardwareNo || 'Not identified' },
    { label: 'Software part number', value: ecu?.softwareNo || 'Not identified' },
    { label: 'Memory region', value: region },
    { label: 'Source firmware file', value: selectedFile || 'Not selected' },
    { label: 'File/checksum validation', value: 'Performed by backend before write' },
    { label: 'Supply voltage', value: voltage === null ? 'Unknown — measurement required' : `${voltage.toFixed(2)} V (${isVoltageSafe ? 'Nominal' : 'Warning'})` },
  ];

  return (
    <div className="p-6 bg-[#1B1C22] border border-[#22242D] max-w-xl w-full mx-auto space-y-6 select-none text-xs text-[#E2E8F0] font-sans">
      <div className="space-y-1 pb-3 border-b border-[#22242D]">
        <h2 className="text-sm font-bold text-[#E2E8F0]">
          Pre-flight safety review
        </h2>
        <p className="text-slate-400">
          Verify target controller parameters before initiating memory write sequence.
        </p>
      </div>

      {/* Un-boxed Document Details */}
      <div className="space-y-2 py-1">
        {checks.map((c, i) => (
          <div key={i} className="flex justify-between items-start py-1 border-b border-[#22242D]/60 text-xs gap-4">
            <span className="text-slate-400 shrink-0">{c.label}</span>
            <span className="font-semibold text-slate-200 text-right break-all max-w-[65%]">{c.value}</span>
          </div>
        ))}
      </div>

      {/* Warning Notice */}
      {!isConnected && (
        <div className="py-2 text-rose-400 text-xs">
          Connect to the ECU before flashing. The backend will reject disconnected writes.
        </div>
      )}
      {ecu?.supportsWrite === false && (
        <div className="py-2 text-rose-400 text-xs">
          Physical programming is disabled for this incomplete ECU definition.
        </div>
      )}
      {isConnected && !isVoltageSafe && (
        <div className="py-2 text-[#F59E0B] text-xs">
          Supply voltage is unavailable or below 12.5V. Verify the measurement source and power supply.
        </div>
      )}

      <label className="flex items-start gap-3 p-3 bg-[#13151E] border border-[#2E313D] rounded-sm text-xs cursor-pointer">
        <input
          type="checkbox"
          checked={backupVerified}
          onChange={(event) => setBackupVerified(event.target.checked)}
          className="mt-0.5"
        />
        <span className="space-y-1">
          <span className="block font-semibold text-slate-200">Backup verified</span>
          <span className="block text-slate-400">
            I have created and verified a readable backup for this ECU before writing flash memory.
          </span>
        </span>
      </label>

      {/* Primary Action Group */}
      <div className="flex items-center justify-end space-x-3 pt-2">
        <button
          onClick={onCancel}
          className="h-8 px-4 bg-[#2A2D38] hover:bg-[#323644] text-slate-300 text-xs font-semibold rounded-sm transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={() => onConfirmWrite(backupVerified)}
          disabled={!canWrite}
          className="h-8 px-5 bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-xs rounded-sm transition-colors"
        >
          Confirm and write flash
        </button>
      </div>
    </div>
  );
};
