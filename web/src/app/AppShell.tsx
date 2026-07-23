import React, { useState, useEffect } from 'react';
import { Header } from '../components/layout/Header';
import { NavRail, WorkspaceTab } from '../components/layout/NavRail';
import { ActivityDrawer } from '../components/layout/ActivityDrawer';
import { CommandPalette } from '../components/CommandPalette';

import { FlashWorkspace } from '../features/flashing/FlashWorkspace';
import { ConnectWorkspace } from '../features/connection/ConnectWorkspace';
import { ReadWorkspace } from '../features/reading/ReadWorkspace';
import { RecoveryWorkspace } from '../features/recovery/RecoveryWorkspace';
import DiagWorkspace from '../workspaces/DiagWorkspace';
import MemoryWorkspace from '../workspaces/MemoryWorkspace';
import TelemetryWorkspace from '../workspaces/TelemetryWorkspace';
import LogsWorkspace from '../workspaces/LogsWorkspace';
import SettingsWorkspace from '../workspaces/SettingsWorkspace';

import { AdapterInfo, EcuIdentityInfo, TelemetryPayload, getPyWebViewGateway } from '../services/pywebview/bridge';
import { globalOperationMachine, OperationState } from '../state/operationMachine';
import { globalCommandRegistry } from '../services/commands/commandRegistry';
import { applyDesktopPreferences } from '../services/theme/preferences';

export const AppShell: React.FC = () => {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('flash');
  const [adapter, setAdapter] = useState<AdapterInfo | null>(null);
  const [ecu, setEcu] = useState<EcuIdentityInfo | null>(null);
  const [ecus, setEcus] = useState<Array<{ id: string; name: string }>>([
    { id: 'me961', name: 'Bosch Motronic ME9.6.1' },
  ]);
  const [activeEcuId, setActiveEcuId] = useState<string>('me961');
  const [telemetry, setTelemetry] = useState<TelemetryPayload | null>(null);
  const [fsmState, setFsmState] = useState<OperationState>(globalOperationMachine.getState());
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [logs, setLogs] = useState<Array<{ time: string; level: string; msg: string }>>([
    { time: new Date().toLocaleTimeString(), level: 'INFO', msg: 'Mackanized flasher desktop engineering session initialized.' },
  ]);

  const gateway = getPyWebViewGateway();

  useEffect(() => {
    // Prevent right-click browser context menu & drag-and-drop navigation
    const handleContextMenu = (e: MouseEvent) => e.preventDefault();
    window.addEventListener('contextmenu', handleContextMenu);

    // Register desktop commands
    globalCommandRegistry.register({
      id: 'file.open',
      title: 'Open Calibration File',
      description: 'Select a binary calibration file via native OS file dialog',
      category: 'File',
      shortcut: 'Ctrl+O',
      safetyLevel: 'safe',
      action: async () => {
        try {
          const res = await gateway.selectCalibrationFile();
          if (res.isValid && res.path) {
            globalOperationMachine.selectFile(res.path);
          }
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Unable to select a calibration file.';
          setLogs((prev) => [
            ...prev,
            { time: new Date().toLocaleTimeString(), level: 'ERROR', msg: message },
          ].slice(-1000));
        }
      },
    });

    globalCommandRegistry.register({
      id: 'app.commandSearch',
      title: 'Command Palette',
      description: 'Search and execute desktop commands',
      category: 'View',
      shortcut: 'Ctrl+K',
      safetyLevel: 'safe',
      action: () => setIsCommandPaletteOpen(true),
    });

    globalCommandRegistry.register({
      id: 'app.settings',
      title: 'Preferences & Settings',
      description: 'Open workstation configuration preferences',
      category: 'Settings',
      shortcut: 'Ctrl+,',
      safetyLevel: 'safe',
      action: () => setActiveTab('settings'),
    });

    globalCommandRegistry.register({
      id: 'ecu.emergencyStop',
      title: 'Emergency Stop',
      description: 'Immediately abort active hardware operation and lock bus',
      category: 'ECU',
      shortcut: 'Esc',
      safetyLevel: 'critical',
      action: () => gateway.emergencyStop(),
    });

    // Global Hotkey Listener
    const handleKeyDown = (e: KeyboardEvent) => {
      const isCtrlOrCmd = e.ctrlKey || e.metaKey;
      if (isCtrlOrCmd && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      } else if (isCtrlOrCmd && e.key.toLowerCase() === 'o') {
        e.preventDefault();
        globalCommandRegistry.execute('file.open');
      } else if (isCtrlOrCmd && e.key === ',') {
        e.preventDefault();
        setActiveTab('settings');
      } else if (e.key === 'Escape') {
        gateway.emergencyStop().catch((err) => console.error('[Emergency Stop] failed:', err));
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    // Load registered ECUs from backend registry
    gateway.getRegisteredEcus().then((res) => {
      if (res && res.length > 0) setEcus(res);
    });

    gateway.getSettings().then((settings) => {
      applyDesktopPreferences(settings);
    }).catch((err) => {
      console.warn('Failed to apply saved desktop preferences:', err);
    });

    // Subscribe to backend telemetry events
    const unsubTelemetry = gateway.subscribeTelemetry((data) => setTelemetry(data));
    const pollTelemetry = async () => setTelemetry(await gateway.getTelemetry());
    const telemetryTimer = window.setInterval(pollTelemetry, 500);
    void pollTelemetry();
    
    // Subscribe to Operation FSM state transitions
    const unsubFsm = globalOperationMachine.subscribe((state, ctx) => {
      setFsmState(state);
      setLogs((prev) => [
        ...prev,
        { time: new Date().toLocaleTimeString(), level: 'INFO', msg: `State: ${state} (${ctx.currentPhaseText})` },
      ].slice(-1000));
    });

    return () => {
      window.removeEventListener('contextmenu', handleContextMenu);
      window.removeEventListener('keydown', handleKeyDown);
      unsubTelemetry();
      unsubFsm();
      window.clearInterval(telemetryTimer);
    };
  }, [gateway]);

  const handleSelectEcu = async (ecuId: string) => {
    setActiveEcuId(ecuId);
    try {
      const updatedInfo = await gateway.setSelectedEcu(ecuId);
      setEcu(updatedInfo);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to select ECU.';
      setLogs((prev) => [
        ...prev,
        { time: new Date().toLocaleTimeString(), level: 'ERROR', msg: message },
      ].slice(-1000));
    }
  };

  const handleConnected = (adapterInfo: AdapterInfo, ecuInfo: EcuIdentityInfo) => {
    setAdapter(adapterInfo);
    setEcu(ecuInfo);
    setActiveTab('flash');
  };

  const renderActiveWorkspace = () => {
    const handleNavigateConnect = () => setActiveTab('connect');
    switch (activeTab) {
      case 'flash':
        return (
          <FlashWorkspace
            ecu={ecu}
            voltage={telemetry?.voltage ?? null}
            isConnected={!!adapter}
            onNavigateToConnect={handleNavigateConnect}
          />
        );
      case 'read':
        return (
          <ReadWorkspace
            ecu={ecu}
            voltage={telemetry?.voltage ?? null}
            isConnected={!!adapter}
            onNavigateToConnect={handleNavigateConnect}
          />
        );
      case 'connect':
        return <ConnectWorkspace onConnected={handleConnected} />;
      case 'diagnostics':
        return <DiagWorkspace isConnected={!!adapter} isSimulation={Boolean(ecu?.isSimulation)} />;
      case 'telemetry':
        return <TelemetryWorkspace telemetryData={telemetry} />;
      case 'memory':
        return <MemoryWorkspace />;
      case 'recovery':
        return <RecoveryWorkspace ecu={ecu} voltage={telemetry?.voltage ?? null} isConnected={!!adapter} />;
      case 'history':
        return <LogsWorkspace logs={logs} />;
      case 'settings':
        return <SettingsWorkspace />;
      default:
        return (
          <FlashWorkspace
            ecu={ecu}
            voltage={telemetry?.voltage ?? null}
            isConnected={!!adapter}
            onNavigateToConnect={handleNavigateConnect}
          />
        );
    }
  };

  const isRecoveryRequired = fsmState === 'recoveryRequired';

  return (
    <div
      className="h-screen w-screen flex flex-col justify-between overflow-hidden font-sans select-none"
      style={{ backgroundColor: 'var(--app-bg)', color: 'var(--text-primary)' }}
    >
      {/* Command Palette Modal (Ctrl+K) */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />

      {/* Persistent High-Density Header */}
      <Header
        ecus={ecus}
        activeEcuId={activeEcuId}
        onSelectEcu={handleSelectEcu}
        ecuInfo={ecu}
        securityState="LOCKED (0x00)"
        isConnected={!!adapter}
        telemetry={telemetry}
      />

      {adapter && ecu?.isSimulation && (
        <div className="h-7 px-3 flex items-center justify-center bg-amber-950 text-amber-300 border-b border-amber-700 text-xs font-bold">
          SIMULATION — no physical ECU is connected; all identities, voltage, reads, and writes are virtual.
        </div>
      )}

      {/* Main Viewport Grid (NavRail | Workspace) */}
      <div className="flex-1 flex overflow-hidden">
        <NavRail
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          isRecoveryRequired={isRecoveryRequired}
        />
        <main className="flex-1 overflow-hidden" style={{ backgroundColor: 'var(--app-main-bg)' }}>
          {renderActiveWorkspace()}
        </main>
      </div>

      {/* Collapsible System Activity Drawer */}
      <ActivityDrawer logs={logs} onClear={() => setLogs([])} />
    </div>
  );
};
