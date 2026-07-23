import React from 'react';
import { FlashProgressPayload } from '../../services/pywebview/bridge';

interface ActiveOperationViewProps {
  operationName: string;
  progress: FlashProgressPayload;
  onAbort: () => void;
}

export const ActiveOperationView: React.FC<ActiveOperationViewProps> = ({
  operationName,
  progress,
  onAbort,
}) => {
  const pct = Math.min(Math.max(progress?.percent || 0, 0), 100);

  return (
    <div className="h-full p-8 max-w-xl mx-auto flex flex-col justify-between select-none font-sans text-xs text-[#E2E8F0]">
      <div className="my-auto space-y-6 w-full">
        {/* Phase Header */}
        <div className="space-y-1">
          <div className="text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
            Active operation
          </div>
          <h1 className="text-lg font-bold text-[#E2E8F0]">{operationName}</h1>
          <p className="text-xs text-slate-400 font-mono-code">
            {progress?.phase || 'Transferring block data...'}
          </p>
        </div>

        {/* Quiet Progress Presentation */}
        <div className="space-y-3">
          <div className="text-3xl font-mono-code font-bold text-[#3B82F6]">
            {pct}%
          </div>

          <div className="w-full h-2 bg-[#1B1C22] rounded-full overflow-hidden border border-[#22242D]">
            <div
              className="h-full bg-[#3B82F6] transition-all duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Un-boxed Metrics */}
        <div className="grid grid-cols-2 gap-3 text-xs pt-2 border-t border-[#22242D] text-slate-300 font-mono-code">
          <div>
            <span className="text-slate-400 font-sans block text-[11px]">Current offset</span>
            <span className="font-semibold text-slate-200">{progress?.currentAddress || 'Unavailable'}</span>
          </div>
          <div>
            <span className="text-slate-400 font-sans block text-[11px]">Transfer rate</span>
            <span className="font-semibold text-slate-200">
              {progress?.transferRateKbps > 0 ? `${progress.transferRateKbps.toFixed(1)} KB/s` : 'Calculating'}
            </span>
          </div>
          <div>
            <span className="text-slate-400 font-sans block text-[11px]">Block index</span>
            <span className="font-semibold text-slate-200">
              {progress?.totalBlocks > 0 ? `#${progress.blockIndex} / ${progress.totalBlocks}` : 'Reported in operation details'}
            </span>
          </div>
          <div>
            <span className="text-slate-400 font-sans block text-[11px]">Estimated remaining</span>
            <span className="font-semibold text-slate-200">
              {progress?.etaSeconds > 0 ? `${progress.etaSeconds} s` : 'Unavailable'}
            </span>
          </div>
        </div>

        {/* Abort Action */}
        <div className="pt-4">
          <button
            onClick={onAbort}
            className="h-8 px-4 bg-[#2A2D38] hover:bg-rose-900/30 text-rose-400 text-xs font-semibold rounded-sm border border-rose-800/40 transition-colors"
          >
            Emergency stop (Esc)
          </button>
        </div>
      </div>
    </div>
  );
};
