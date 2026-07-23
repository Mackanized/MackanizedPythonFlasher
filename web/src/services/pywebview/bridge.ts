/**
 * PyWebView Typed Frontend Bridge Gateway
 * 
 * Enforces typed contracts between React frontend and Python backend.
 * Wraps PyWebView window.pywebview.api. The browser-only build uses an explicit
 * simulator; the native bridge fails closed when the Python backend is absent.
 */

import { pyClient } from '../bridge/PyWebViewClient';

export interface AdapterInfo {
  id: string;
  name: string;
  type: 'j2534' | 'kvaser' | 'socketcan' | 'mock';
  isAvailable: boolean;
}

export interface EcuIdentityInfo {
  name: string;
  vehicle: string;
  hardwareNo: string;
  softwareNo: string;
  mcu: string;
  protocol: string;
  securityAlgo: string;
  flashSizeKb: number;
  eepromSizeKb: number;
  isSimulation?: boolean;
  supportsRead?: boolean;
  supportsWrite?: boolean;
  supportsRecovery?: boolean;
  developmentStatus?: string;
  readRegions?: string[];
  writeRegions?: string[];
}

export interface TelemetryPayload {
  voltage: number | null;
  voltage_status: 'normal' | 'warning' | 'critical' | 'unknown';
  can_bus_load: number | null;
  cpu_usage_pct: number | null;
  memory_usage_mb: number | null;
  tx_fps: number | null;
  rx_fps: number | null;
  is_simulation?: boolean;
  source?: string;
}

export interface OperationStartResult {
  accepted: boolean;
  operationId: string;
}

export interface FlashProgressPayload {
  phase: string;
  percent: number;
  currentAddress: string;
  blockIndex: number;
  totalBlocks: number;
  bytesTransferred: number;
  transferRateKbps: number;
  etaSeconds: number;
}

export interface OperationStatus {
  operationId: string;
  operation: 'read' | 'write' | 'info' | 'recovery' | '';
  active: boolean;
  state: 'idle' | 'running' | 'completed' | 'failed' | 'cancelled' | 'recovery_required';
  phase: string;
  percent: number;
  speedKbps: number;
  details: string;
  success: boolean | null;
  message: string;
}

export interface DtcItem {
  code: string;
  description: string;
  status: 'Active' | 'Pending' | 'History';
  severity: 'Low' | 'Medium' | 'Critical';
}

export interface SelectedFilePayload {
  path: string;
  filename: string;
  sizeBytes: number;
  isValid: boolean;
  suggestedRegion?: string;
}

export interface WorkstationSettingsPayload {
  theme: string;
  densityMode: string;
  defaultAdapter: string;
  j2534Dll: string;
  stnPort?: string;
  socketcanInterface?: string;
  baudrate: number;
  disablePreflight: boolean;
}

export interface ScannedPort {
  device: string;
  description: string;
  manufacturer: string;
  likelyAdapter: boolean;
}

export interface PyWebViewGateway {
  getAdapters(): Promise<AdapterInfo[]>;
  connectAdapter(adapterId: string): Promise<boolean>;
  disconnectAdapter(): Promise<boolean>;
  isConnected(): Promise<boolean>;
  getTelemetry(): Promise<TelemetryPayload>;
  getRegisteredEcus(): Promise<Array<{ id: string; name: string }>>;
  setSelectedEcu(ecuId: string): Promise<EcuIdentityInfo>;
  readEcuInfo(): Promise<EcuIdentityInfo>;
  selectCalibrationFile(region?: string): Promise<SelectedFilePayload>;
  getRecentFiles(): Promise<string[]>;
  getSettings(): Promise<WorkstationSettingsPayload>;
  updateSettings(settings: Partial<WorkstationSettingsPayload>): Promise<boolean>;
  scanSerialPorts(): Promise<ScannedPort[]>;
  startFlashRead(region: string): Promise<OperationStartResult>;
  startFlashWrite(filePath: string, region: string, operatorConfirmed?: boolean, backupVerified?: boolean): Promise<OperationStartResult>;
  startRecoveryFlash(operatorConfirmed?: boolean, backupVerified?: boolean): Promise<OperationStartResult>;
  getOperationStatus(): Promise<OperationStatus>;
  emergencyStop(): Promise<boolean>;
  readDtcs(): Promise<DtcItem[]>;
  clearDtcs(): Promise<boolean>;
  subscribeTelemetry(callback: (data: TelemetryPayload) => void): () => void;
  subscribeFlashProgress(callback: (data: FlashProgressPayload) => void): () => void;
}

class MockPyWebViewGateway implements PyWebViewGateway {
  private telemetryListeners: Set<(data: TelemetryPayload) => void> = new Set();
  private flashProgressListeners: Set<(data: FlashProgressPayload) => void> = new Set();
  private mockRecentFiles: string[] = [];
  private connected = false;
  private selectedEcuId = 'me961';
  private operationTimer: ReturnType<typeof setInterval> | null = null;
  private operationStatus: OperationStatus = {
    operationId: '', operation: '', active: false, state: 'idle', phase: 'Idle',
    percent: 0, speedKbps: 0, details: 'Connect to the mock ECU to begin.',
    success: null, message: '',
  };

  async getAdapters(): Promise<AdapterInfo[]> {
    return [
      { id: 'mock', name: 'MockAdapter (Offline Simulator)', type: 'mock', isAvailable: true },
      { id: 'kvaser', name: 'Kvaser hardware unavailable in browser simulator', type: 'kvaser', isAvailable: false },
      { id: 'j2534', name: 'J2534 hardware unavailable in browser simulator', type: 'j2534', isAvailable: false },
    ];
  }

  async connectAdapter(adapterId: string): Promise<boolean> {
    if (adapterId !== 'mock') return false;
    this.connected = true;
    return true;
  }

  async disconnectAdapter(): Promise<boolean> {
    if (this.operationStatus.active) return false;
    this.connected = false;
    return true;
  }

  async isConnected(): Promise<boolean> {
    return this.connected;
  }

  async getTelemetry(): Promise<TelemetryPayload> {
    return {
      voltage: this.connected ? 13.8 : null,
      voltage_status: this.connected ? 'normal' : 'unknown',
      can_bus_load: this.connected ? 18.0 : 0,
      cpu_usage_pct: 3.2,
      memory_usage_mb: 142.0,
      tx_fps: this.connected ? 180 : 0,
      rx_fps: this.connected ? 210 : 0,
      is_simulation: true,
      source: 'browser-simulator',
    };
  }

  async getRegisteredEcus(): Promise<Array<{ id: string; name: string }>> {
    return [
      { id: 'me961', name: 'Bosch Motronic ME9.6.1' },
      { id: 'me96', name: 'Bosch Motronic ME9.6' },
      { id: 't52', name: 'Saab Trionic 5.2' },
      { id: 't55', name: 'Saab Trionic 5.5' },
      { id: 't7', name: 'Saab Trionic 7' },
      { id: 't8', name: 'Saab Trionic 8' },
      { id: 'edc16c39', name: 'Bosch EDC16C39' },
      { id: 'edc17c19', name: 'Bosch EDC17C19' },
    ];
  }

  async setSelectedEcu(ecuId: string): Promise<EcuIdentityInfo> {
    const registered = await this.getRegisteredEcus();
    if (!registered.some((ecu) => ecu.id === ecuId)) {
      throw new Error(`Unknown simulated ECU: ${ecuId}`);
    }
    this.selectedEcuId = ecuId;
    return this.mockEcuInfo();
  }

  async readEcuInfo(): Promise<EcuIdentityInfo> {
    if (!this.connected) throw new Error('Connect to the mock ECU before identification.');
    return this.mockEcuInfo();
  }

  private mockEcuInfo(): EcuIdentityInfo {
    const trionicProfiles: Record<string, Partial<EcuIdentityInfo>> = {
      t52: {
        name: 'Saab Trionic 5.2', vehicle: 'Saab classic 900 / 9000',
        mcu: 'Motorola 68k / Flash 128KB', protocol: 'T5 native CAN loader',
        securityAlgo: 'Loader command acknowledgement', flashSizeKb: 128,
        readRegions: ['full'], writeRegions: ['full'],
      },
      t55: {
        name: 'Saab Trionic 5.5', vehicle: 'Saab 900 / 9000',
        mcu: 'Motorola 68k / Flash 256KB', protocol: 'T5 native CAN loader',
        securityAlgo: 'Loader command acknowledgement', flashSizeKb: 256,
        readRegions: ['full'], writeRegions: ['full'],
      },
      t7: {
        name: 'Saab Trionic 7', vehicle: 'Saab 9-3 / 9-5',
        mcu: 'Trionic 7 / Flash 512KB', protocol: 'Saab KWP2000 rows over CAN',
        securityAlgo: 'KWP SecurityAccess 0x05/0x06', flashSizeKb: 512,
        readRegions: ['full'], writeRegions: ['full'],
      },
      t8: {
        name: 'Saab Trionic 8', vehicle: 'Saab 9-3 B207 / B284',
        mcu: 'MPC5xx / Flash 1MB', protocol: 'GMLAN/ISO-TP plus SRAM loader',
        securityAlgo: 'GMLAN SecurityAccess 0x01/0x02', flashSizeKb: 1024,
        readRegions: ['full', 'main', 'boot'], writeRegions: ['main'],
      },
    };
    const base: EcuIdentityInfo = {
      name: 'Bosch Motronic ME9.6.1',
      vehicle: 'Saab 9-3 2.8T V6',
      hardwareNo: '0261208961',
      softwareNo: '1037383491',
      mcu: 'MPC564 / Flash 2MB',
      protocol: 'UDS over CAN (ISO 15765)',
      securityAlgo: 'Bosch Key Algo (0x27)',
      flashSizeKb: 2048,
      eepromSizeKb: 2,
      isSimulation: true,
      supportsRead: true,
      supportsWrite: true,
      supportsRecovery: true,
      developmentStatus: 'simulator',
      readRegions: ['full', 'calibration'],
      writeRegions: ['full', 'calibration'],
    };
    return { ...base, ...(trionicProfiles[this.selectedEcuId] ?? {}) };
  }

  async selectCalibrationFile(region = 'full'): Promise<SelectedFilePayload> {
    const identity = this.mockEcuInfo();
    const mockFile = `mock://firmware/${this.selectedEcuId}_${region}.bin`;
    this.mockRecentFiles.unshift(mockFile);
    return {
      path: mockFile,
      filename: `${this.selectedEcuId.toUpperCase()}_${region}_simulated.bin`,
      sizeBytes: identity.flashSizeKb * 1024,
      isValid: true,
      suggestedRegion: (identity.writeRegions ?? []).includes(region)
        ? region
        : identity.writeRegions?.[0] || 'full',
    };
  }

  async getRecentFiles(): Promise<string[]> {
    return this.mockRecentFiles;
  }

  private mockSettings: WorkstationSettingsPayload = {
    theme: 'dark',
    densityMode: 'standard',
    defaultAdapter: 'mock',
    j2534Dll: '',
    stnPort: 'COM3',
    socketcanInterface: 'can0',
    baudrate: 500000,
    disablePreflight: true,
  };

  async getSettings(): Promise<WorkstationSettingsPayload> {
    return { ...this.mockSettings };
  }

  async updateSettings(settings: Partial<WorkstationSettingsPayload>): Promise<boolean> {
    this.mockSettings = { ...this.mockSettings, ...settings };
    return true;
  }

  async scanSerialPorts(): Promise<ScannedPort[]> {
    return [
      { device: 'COM3', description: 'STN2120 OBDLink Adapter', manufacturer: 'SparkFun', likelyAdapter: true },
      { device: 'COM5', description: 'USB Serial Device', manufacturer: 'FTDI', likelyAdapter: true },
      { device: 'COM1', description: 'Communications Port', manufacturer: '(Standard port types)', likelyAdapter: false },
    ];
  }

  async startFlashRead(region: string): Promise<OperationStartResult> {
    return this.startMockOperation('read', region);
  }

  async startFlashWrite(filePath: string, region: string, operatorConfirmed = false, backupVerified = false): Promise<OperationStartResult> {
    if (!filePath || !operatorConfirmed || !backupVerified) return { accepted: false, operationId: '' };
    return this.startMockOperation('write', region);
  }

  async startRecoveryFlash(operatorConfirmed = false, backupVerified = false): Promise<OperationStartResult> {
    if (!operatorConfirmed || !backupVerified || this.selectedEcuId !== 't8') {
      return { accepted: false, operationId: '' };
    }
    return this.startMockOperation('recovery', 't8');
  }

  async getOperationStatus(): Promise<OperationStatus> {
    return { ...this.operationStatus };
  }

  async emergencyStop(): Promise<boolean> {
    if (this.operationTimer) clearInterval(this.operationTimer);
    this.operationTimer = null;
    this.operationStatus = {
      ...this.operationStatus,
      active: false,
      state: 'cancelled',
      phase: 'Cancelled',
      success: false,
      message: 'Mock operation cancelled.',
      details: 'Mock operation cancelled by operator.',
    };
    return true;
  }

  async readDtcs(): Promise<DtcItem[]> {
    return [
      { code: 'P0300', description: 'Random/Multiple Cylinder Misfire Detected', status: 'Active', severity: 'Medium' },
      { code: 'P0100', description: 'Mass or Volume Air Flow Circuit Malfunction', status: 'Pending', severity: 'Low' },
      { code: 'P0601', description: 'Internal Control Module Memory Check Sum Error', status: 'History', severity: 'Critical' },
    ];
  }

  async clearDtcs(): Promise<boolean> {
    return true;
  }

  subscribeTelemetry(callback: (data: TelemetryPayload) => void): () => void {
    this.telemetryListeners.add(callback);
    return () => this.telemetryListeners.delete(callback);
  }

  subscribeFlashProgress(callback: (data: FlashProgressPayload) => void): () => void {
    this.flashProgressListeners.add(callback);
    return () => this.flashProgressListeners.delete(callback);
  }

  private startMockOperation(operation: 'read' | 'write' | 'recovery', region: string): OperationStartResult {
    if (!this.connected || this.operationStatus.active) return { accepted: false, operationId: '' };
    if (this.operationTimer) clearInterval(this.operationTimer);
    this.operationStatus = {
      operationId: `mock-${operation}-${Date.now()}`,
      operation,
      active: true,
      state: 'running',
      phase: operation === 'write'
        ? 'Entering simulated programming session'
        : operation === 'recovery' ? 'Entering simulated recovery session' : 'Entering simulated read session',
      percent: 0,
      speedKbps: 0,
      details: `Preparing ${region} ${operation} in offline simulator.`,
      success: null,
      message: '',
    };
    this.operationTimer = setInterval(() => {
      const next = Math.min(100, this.operationStatus.percent + 5);
      const phase = operation === 'write'
        ? (next < 10 ? 'Simulated erase' : next < 90 ? 'Simulated programming' : 'Simulated verification')
        : operation === 'recovery'
          ? (next < 45 ? 'Simulated T8 recovery session' : next < 90 ? 'Simulated recovery loader upload' : 'Simulated recovery loader start')
        : (next < 90 ? 'Reading simulated ECU memory' : 'Verifying simulated read');
      this.operationStatus = {
        ...this.operationStatus,
        percent: next,
        phase,
        speedKbps: 192.0,
        details: `${phase}: ${next}%`,
      };
      this.flashProgressListeners.forEach((listener) => listener({
        phase,
        percent: next,
        currentAddress: `0x${Math.round(next / 100 * 0x200000).toString(16).padStart(8, '0')}`,
        blockIndex: Math.round(next / 100 * 512),
        totalBlocks: 512,
        bytesTransferred: Math.round(next / 100 * 0x200000),
        transferRateKbps: 192.0,
        etaSeconds: Math.round((100 - next) / 5),
      }));
      if (next >= 100) {
        if (this.operationTimer) clearInterval(this.operationTimer);
        this.operationTimer = null;
        this.operationStatus = {
          ...this.operationStatus,
          active: false,
          state: 'completed',
          phase: 'Completed',
          success: true,
          message: `Mock ${operation} completed successfully.`,
          details: `Offline simulator ${operation} and verification completed.`,
        };
      }
    }, 100);
    return { accepted: true, operationId: this.operationStatus.operationId };
  }
}

class PyWebViewClientGateway implements PyWebViewGateway {
  private api: Record<string, unknown>;

  constructor(api: Record<string, unknown>) {
    this.api = api;
  }

  /**
   * Invoke a backend method whose caller needs to know WHY it failed (connect,
   * identify, file pick, settings save, etc). Only falls back to a generic
   * message when the method is genuinely absent from the bridge; otherwise the
   * real backend error (with its real message) propagates to the caller
   * instead of being swallowed into an unhelpful "backend unavailable" string.
   */
  private async invokeAction<T>(method: string, unavailableMessage: string, ...args: unknown[]): Promise<T> {
    if (!this.api[method]) {
      throw new Error(unavailableMessage);
    }
    return pyClient.invoke<T>(method, ...args);
  }

  async getAdapters(): Promise<AdapterInfo[]> {
    try {
      if (this.api.getAdapters) return await pyClient.invoke<AdapterInfo[]>('getAdapters');
    } catch (e) {
      console.warn('[PyWebView Gateway Warning] getAdapters error:', e);
    }
    return [];
  }

  async connectAdapter(adapterId: string): Promise<boolean> {
    return this.invokeAction<boolean>('connectAdapter', 'Unable to connect: backend unavailable.', adapterId);
  }

  async disconnectAdapter(): Promise<boolean> {
    return this.invokeAction<boolean>('disconnectAdapter', 'Unable to disconnect: backend unavailable.');
  }

  async isConnected(): Promise<boolean> {
    try {
      if (this.api.isConnected) return await pyClient.invoke<boolean>('isConnected');
    } catch (e) {
      console.warn('[PyWebView Gateway Warning] isConnected error:', e);
    }
    return false;
  }

  async getTelemetry(): Promise<TelemetryPayload> {
    try {
      if (this.api.getTelemetry) return await pyClient.invoke<TelemetryPayload>('getTelemetry');
    } catch (e) {
      console.warn('[PyWebView Gateway Warning] getTelemetry error:', e);
    }
    return {
      voltage: null, voltage_status: 'unknown', can_bus_load: null,
      cpu_usage_pct: null, memory_usage_mb: null, tx_fps: null, rx_fps: null,
      is_simulation: false, source: 'backend-unavailable',
    };
  }

  async getRegisteredEcus(): Promise<Array<{ id: string; name: string }>> {
    try {
      if (this.api.getRegisteredEcus) return await pyClient.invoke<Array<{ id: string; name: string }>>('getRegisteredEcus');
    } catch (e) {
      console.warn('[PyWebView Gateway Warning] getRegisteredEcus error:', e);
    }
    return [];
  }

  async setSelectedEcu(ecuId: string): Promise<EcuIdentityInfo> {
    return this.invokeAction<EcuIdentityInfo>('setSelectedEcu', 'Unable to select ECU: backend unavailable.', ecuId);
  }

  async readEcuInfo(): Promise<EcuIdentityInfo> {
    return this.invokeAction<EcuIdentityInfo>('readEcuInfo', 'Unable to identify ECU: backend unavailable.');
  }

  async selectCalibrationFile(region = 'full'): Promise<SelectedFilePayload> {
    return this.invokeAction<SelectedFilePayload>(
      'selectCalibrationFile',
      'Unable to open the file dialog: backend unavailable.',
      region,
    );
  }

  async getRecentFiles(): Promise<string[]> {
    try {
      if (this.api.getRecentFiles) return await pyClient.invoke<string[]>('getRecentFiles');
    } catch (e) {
      console.warn('[PyWebView Gateway Warning] getRecentFiles error:', e);
    }
    return [];
  }

  async getSettings(): Promise<WorkstationSettingsPayload> {
    try {
      if (this.api.getSettings) return await pyClient.invoke<WorkstationSettingsPayload>('getSettings');
    } catch (e) {
      console.warn('[PyWebView Gateway Warning] getSettings error:', e);
    }
    return { theme: 'dark', densityMode: 'standard', defaultAdapter: '', j2534Dll: '', baudrate: 500000, disablePreflight: true };
  }

  async updateSettings(settings: Partial<WorkstationSettingsPayload>): Promise<boolean> {
    return this.invokeAction<boolean>('updateSettings', 'Unable to save settings: backend unavailable.', settings);
  }

  async scanSerialPorts(): Promise<ScannedPort[]> {
    return this.invokeAction<ScannedPort[]>('scanSerialPorts', 'Unable to scan serial ports: backend unavailable.');
  }

  async startFlashRead(region: string): Promise<OperationStartResult> {
    return this.invokeAction<OperationStartResult>('startFlashRead', 'Unable to start read: backend unavailable.', region);
  }

  async startFlashWrite(filePath: string, region: string, operatorConfirmed = false, backupVerified = false): Promise<OperationStartResult> {
    return this.invokeAction<OperationStartResult>(
      'startFlashWrite',
      'Unable to start write: backend unavailable.',
      filePath, region, operatorConfirmed, backupVerified,
    );
  }

  async startRecoveryFlash(operatorConfirmed = false, backupVerified = false): Promise<OperationStartResult> {
    return this.invokeAction<OperationStartResult>(
      'startRecoveryFlash',
      'Unable to start recovery: backend unavailable.',
      operatorConfirmed, backupVerified,
    );
  }

  async getOperationStatus(): Promise<OperationStatus> {
    try {
      if (this.api.getOperationStatus) return await pyClient.invoke<OperationStatus>('getOperationStatus');
    } catch (e) {
      console.warn('[PyWebView Gateway Warning] getOperationStatus error:', e);
    }
    return {
      operationId: '', operation: '', active: false, state: 'failed', phase: 'Backend unavailable',
      percent: 0, speedKbps: 0, details: 'Unable to read operation status.',
      success: false, message: 'Backend unavailable.',
    };
  }

  async emergencyStop(): Promise<boolean> {
    return this.invokeAction<boolean>('emergencyStop', 'Unable to send emergency stop: backend unavailable.');
  }

  async readDtcs(): Promise<DtcItem[]> {
    return this.invokeAction<DtcItem[]>('readDtcs', 'Unable to read DTCs: backend unavailable.');
  }

  async clearDtcs(): Promise<boolean> {
    return this.invokeAction<boolean>('clearDtcs', 'Unable to clear DTCs: backend unavailable.');
  }

  subscribeTelemetry(callback: (data: TelemetryPayload) => void): () => void {
    if (typeof this.api?.subscribeTelemetry === 'function') {
      try {
        return this.api.subscribeTelemetry(callback);
      } catch (e) {
        console.warn('[PyWebView Gateway Warning] subscribeTelemetry error:', e);
      }
    }
    return () => undefined;
  }

  subscribeFlashProgress(callback: (data: FlashProgressPayload) => void): () => void {
    if (typeof this.api?.subscribeFlashProgress === 'function') {
      try {
        return this.api.subscribeFlashProgress(callback);
      } catch (e) {
        console.warn('[PyWebView Gateway Warning] subscribeFlashProgress error:', e);
      }
    }
    return () => undefined;
  }
}

let gatewayInstance: PyWebViewGateway | null = null;
let upgradeListenerAttached = false;

// Factory returns one long-lived gateway so simulator timers are not duplicated.
//
// PyWebView only injects `window.pywebview.api` after its native host fires
// `NavigationCompleted` on the page that has ALREADY loaded and run this module,
// so on first call in the desktop app the bridge is reliably still absent.
// Falling back to the mock here is correct, but the choice must not be
// permanent: once `pywebviewready` fires we swap the live singleton for the
// real bridge so callers who fetch a fresh gateway on their next render (e.g.
// React components re-invoking this factory on re-render) pick up the desktop
// backend instead of being stuck on the browser simulator for the session.
export function getPyWebViewGateway(): PyWebViewGateway {
  if (gatewayInstance && !(gatewayInstance instanceof MockPyWebViewGateway)) return gatewayInstance;

  if (typeof window !== 'undefined' && (window as any).pywebview?.api) {
    gatewayInstance = new PyWebViewClientGateway((window as any).pywebview.api);
    return gatewayInstance;
  }

  if (gatewayInstance) return gatewayInstance;
  gatewayInstance = new MockPyWebViewGateway();

  if (typeof window !== 'undefined' && !upgradeListenerAttached) {
    upgradeListenerAttached = true;
    window.addEventListener('pywebviewready', () => {
      if ((window as any).pywebview?.api) {
        gatewayInstance = new PyWebViewClientGateway((window as any).pywebview.api);
      }
    }, { once: true });
  }

  return gatewayInstance;
}
