import React, { useState, useEffect } from 'react';
import { AdapterInfo, EcuIdentityInfo, getPyWebViewGateway } from '../../services/pywebview/bridge';

interface ConnectWorkspaceProps {
  onConnected: (adapter: AdapterInfo, ecu: EcuIdentityInfo) => void;
}

export const ConnectWorkspace: React.FC<ConnectWorkspaceProps> = ({ onConnected }) => {
  const [adapters, setAdapters] = useState<AdapterInfo[]>([]);
  const [selectedAdapterId, setSelectedAdapterId] = useState<string>('');
  const [isConnecting, setIsConnecting] = useState(false);
  const [detectedEcu, setDetectedEcu] = useState<EcuIdentityInfo | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const gateway = getPyWebViewGateway();

  useEffect(() => {
    let mounted = true;
    const loadAdapters = async () => {
      const live = getPyWebViewGateway();
      const [adapterList, settings] = await Promise.all([
        live.getAdapters(),
        live.getSettings(),
      ]);
      if (!mounted) return;
      setAdapters(adapterList);
      const preferred = adapterList.find((adapter) => (
        adapter.id === settings.defaultAdapter && adapter.isAvailable
      ));
      const fallback = adapterList.find((adapter) => adapter.isAvailable) ?? adapterList[0];
      setSelectedAdapterId(preferred?.id ?? fallback?.id ?? '');
    };
    const reportError = (err: unknown) => {
      setErrorMsg(err instanceof Error ? err.message : 'Adapter discovery failed.');
    };
    void loadAdapters().catch(reportError);

    // The desktop bridge lands asynchronously after this component may have
    // already mounted and queried the browser-simulator gateway; reload once
    // the real backend becomes available so the list reflects actual hardware.
    const handleReady = () => void loadAdapters().catch(reportError);
    window.addEventListener('pywebviewready', handleReady);
    return () => {
      mounted = false;
      window.removeEventListener('pywebviewready', handleReady);
    };
  }, [gateway]);

  const handleConnectSequence = async () => {
    setIsConnecting(true);
    setErrorMsg(null);

    try {
      const ok = await gateway.connectAdapter(selectedAdapterId);
      if (!ok) throw new Error("Adapter initialization failed. Verify USB connection.");

      const ecuInfo = await gateway.readEcuInfo();
      setDetectedEcu(ecuInfo);

      const adapter = adapters.find((a) => a.id === selectedAdapterId) || adapters[0];
      onConnected(adapter, ecuInfo);
    } catch (err: any) {
      try {
        if (await gateway.isConnected()) await gateway.disconnectAdapter();
      } catch (cleanupErr) {
        console.warn('[ConnectWorkspace] Cleanup disconnect failed:', cleanupErr);
      }
      setErrorMsg(err.message || "Failed to establish controller connection.");
    } finally {
      setIsConnecting(false);
    }
  };

  return (
    <div
      className="h-full flex flex-col justify-between select-none font-sans text-xs"
      style={{ padding: 'var(--workspace-padding)', backgroundColor: 'var(--bg-surface-base)', color: 'var(--text-primary)' }}
    >
      <div className="max-w-xl mx-auto w-full space-y-6 my-auto">
        <div className="space-y-1">
          <h1 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Connect hardware interface</h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Select your PassThru or CAN hardware adapter to query the target vehicle bus and identify the controller.
          </p>
        </div>

        {/* Adapter Selector */}
        <div className="space-y-2">
          <label className="text-xs font-semibold block" style={{ color: 'var(--text-primary)' }}>
            Hardware interface adapter
          </label>
          <select
            value={selectedAdapterId}
            onChange={(e) => setSelectedAdapterId(e.target.value)}
            className="w-full px-3 font-semibold text-xs rounded-sm border focus:outline-none focus:border-[#3B82F6]"
            style={{ height: 'var(--control-height)', backgroundColor: 'var(--control-bg)', color: 'var(--text-primary)', borderColor: 'var(--panel-border)' }}
          >
            {adapters.map((a) => (
              <option key={a.id} value={a.id} disabled={!a.isAvailable} style={{ backgroundColor: 'var(--panel-bg)', color: 'var(--text-primary)' }}>
                {a.name} ({a.type.toUpperCase()})
              </option>
            ))}
          </select>
        </div>

        {/* Error Notice */}
        {errorMsg && (
          <div className="py-2 text-[#EF4444] text-xs">
            Connection error: {errorMsg}
          </div>
        )}

        {/* Detected ECU Details */}
        {detectedEcu && (
          <div className="py-2 border-t border-b border-[#22242D] space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">Controller identified</span>
              <span className="font-semibold text-[#10B981]">{detectedEcu.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Hardware part number</span>
              <span className="font-mono-code text-slate-200">{detectedEcu.hardwareNo}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Software part number</span>
              <span className="font-mono-code text-slate-200">{detectedEcu.softwareNo}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Protocol</span>
              <span className="font-mono-code text-slate-300">{detectedEcu.protocol}</span>
            </div>
          </div>
        )}

        {/* Primary Action Button */}
        <div>
          <button
            onClick={handleConnectSequence}
            disabled={isConnecting}
            className="w-full h-9 bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 text-white font-semibold text-xs rounded-sm transition-colors"
          >
            {isConnecting ? 'Connecting to vehicle bus...' : 'Establish vehicle connection'}
          </button>
        </div>
      </div>
    </div>
  );
};
