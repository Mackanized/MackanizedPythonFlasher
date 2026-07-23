/**
 * Typed PyWebView Desktop Client Bridge
 * Wraps window.pywebview.api calls with strict promises, timeout guards, and development mocks.
 */

import { BridgeResponse } from './bridge.types';
import { PyWebViewBridgeError } from './bridge.errors';

export class PyWebViewClient {
  private timeoutMs: number = 30000;

  /**
   * Invoke a named method exposed by Python API on window.pywebview.api
   */
  public async invoke<T = unknown>(methodName: string, ...args: unknown[]): Promise<T> {
    let pyApi = this.getPyApi();

    if (!pyApi && typeof window !== 'undefined' && ('pywebview' in window || (window as any).pywebview)) {
      await new Promise<void>((resolve) => {
        if ((window as any).pywebview?.api) return resolve();
        const handler = () => {
          window.removeEventListener('pywebviewready', handler);
          resolve();
        };
        window.addEventListener('pywebviewready', handler);
        setTimeout(() => {
          window.removeEventListener('pywebviewready', handler);
          resolve();
        }, 2500);
      });
      pyApi = this.getPyApi();
    }

    if (!pyApi || typeof pyApi[methodName] !== 'function') {
      // In development mode without PyWebView window, use mock response provider
      return this.handleDevMock<T>(methodName, ...args);
    }

    try {
      const responsePromise = pyApi[methodName](...args) as Promise<BridgeResponse<T>>;
      const response = await this.withTimeout(responsePromise, this.timeoutMs, methodName);

      if (!response || typeof response !== 'object') {
        return response as T;
      }

      if (response.success === false) {
        throw new PyWebViewBridgeError(
          response.error?.code || 'ERR_BACKEND_FAILURE',
          response.error?.message || `Backend operation '${methodName}' failed`,
          response.error?.details
        );
      }

      return (response.data !== undefined ? response.data : response) as T;
    } catch (err: any) {
      if (err instanceof PyWebViewBridgeError) {
        throw err;
      }
      throw new PyWebViewBridgeError(
        'ERR_BRIDGE_INVOCATION',
        err?.message || `Failed to execute backend method '${methodName}'`,
        { methodName, args }
      );
    }
  }

  private getPyApi(): any {
    if (typeof window !== 'undefined' && (window as any).pywebview && (window as any).pywebview.api) {
      return (window as any).pywebview.api;
    }
    return null;
  }

  private withTimeout<T>(promise: Promise<T>, ms: number, methodName: string): Promise<T> {
    let timeoutId: any;
    const timeoutPromise = new Promise<never>((_, reject) => {
      timeoutId = setTimeout(() => {
        reject(new PyWebViewBridgeError('ERR_TIMEOUT', `Backend request '${methodName}' timed out after ${ms}ms`));
      }, ms);
    });

    return Promise.race([promise, timeoutPromise]).finally(() => clearTimeout(timeoutId));
  }

  /**
   * Mock implementations for Vite development server (browser mode without PyWebView)
   */
  private async handleDevMock<T>(methodName: string, ...args: unknown[]): Promise<T> {
    console.warn(`[PyWebView Mock Dev Mode] Invoking backend method: '${methodName}'`, args);
    await new Promise((res) => setTimeout(res, 200));

    switch (methodName) {
      case 'getAdapters':
      case 'list_adapters':
        return [
          { id: 'kvaser_0', name: 'Kvaser Leaf Light v2 (Channel 0)', type: 'kvaser', channel: 0, available: true, isAvailable: true },
          { id: 'j2534_0', name: 'DrewTech MongoosePro GM II', type: 'j2534', channel: 0, available: true, isAvailable: true, dll_path: 'C:\\Windows\\System32\\mon32.dll' },
          { id: 'mock', name: 'Virtual Simulation Adapter', type: 'mock', channel: 0, available: true, isAvailable: true }
        ] as unknown as T;

      case 'connectAdapter':
        return true as unknown as T;

      case 'connect_adapter':
        return {
          connected: true,
          adapter_name: 'Virtual Simulation Adapter',
          baudrate: 500000,
          ecu_family: 'Bosch ME9.6.1',
          battery_voltage: 13.7,
          security_access: true,
          active_session: 'Programming'
        } as unknown as T;

      case 'disconnectAdapter':
        return true as unknown as T;

      case 'disconnect_adapter':
        return { connected: false } as unknown as T;

      case 'readEcuInfo':
        return {
          name: 'Bosch ME9.6.1',
          vehicle: 'Saab 9-3 2.8T V6',
          hardwareNo: '12592144',
          softwareNo: '55562109',
          mcu: 'MPC564 / Flash 2MB',
          protocol: 'GMLAN over ISO-TP',
          securityAlgo: 'SecurityAccess level 0x01',
          flashSizeKb: 2048,
          eepromSizeKb: 2,
          vin: '1YSFH66387XXXXXXX',
          isSimulation: true,
          supportsRead: true,
          supportsWrite: true,
          supportsRecovery: true,
          readRegions: ['full', 'calibration'],
          writeRegions: ['full', 'calibration'],
        } as unknown as T;

      case 'detect_ecu':
      case 'read_ecu_identity':
        return {
          ecu_family: 'Bosch ME9.6.1',
          display_name: 'Bosch ME9.6.1 (GM Saab/Holden V6)',
          vin: '1YSFH66387XXXXXXX',
          hardware_type: '12592144',
          software_id: '55562109',
          supplier: 'BOSCH',
          diag_address: '0x7E0',
          programming_date: '2024-05-12',
          raw_pids: { vin: '1YSFH66387XXXXXXX', hardware_type: '12592144', main_os: '55562109' }
        } as unknown as T;

      case 'getMemoryMap':
      case 'get_memory_map':
        return {
          ecu_name: 'Bosch ME9.6.1',
          total_flash_size: 0x200000,
          regions: [
            { name: 'calibration', start_address: 0x1C2000, end_address: 0x1F0000, size_bytes: 188416, filename: 'ME961_Calibration.bin', readable: true, writable: true, protected: false },
            { name: 'full', start_address: 0x000000, end_address: 0x200000, size_bytes: 2097152, filename: 'ME961_Full.bin', readable: true, writable: true, protected: false }
          ]
        } as unknown as T;

      case 'validateFirmwareFile':
      case 'validate_firmware_file':
        return {
          valid: true,
          file_name: String(args[0] || 'ME961_Stage1_v2.bin'),
          file_size: 2097152,
          detected_format: 'Raw Binary (BIN)',
          target_compatible: true,
          software_id_match: true,
          checksum_valid: true,
          checksum_name: 'Bosch CCP 0xC001 CRC',
          calculated_checksum: '0xA4F1',
          warnings: [],
          errors: [],
          suggested_region: 'full'
        } as unknown as T;

      case 'readDtcs':
      case 'read_dtcs':
        return [
          { code: 'P0300', status: 'active', description: 'Random/Multiple Cylinder Misfire Detected', severity: 'high', raw_status_byte: '0xAF', freeze_frame: { 'RPM': '2450', 'Coolant': '88 °C', 'Voltage': '13.6 V' } },
          { code: 'P0420', status: 'active', description: 'Catalyst System Efficiency Below Threshold (Bank 1)', severity: 'medium', raw_status_byte: '0x2F' },
          { code: 'P0113', status: 'stored', description: 'Intake Air Temperature Circuit High Input', severity: 'low', raw_status_byte: '0x08' }
        ] as unknown as T;

      case 'clearDtcs':
      case 'clear_dtcs':
        return { success: true, cleared_count: 3 } as unknown as T;

      case 'selectCalibrationFile':
        return {
          path: '/firmware/ME961_Stage1_v2.bin',
          filename: 'ME961_Stage1_v2.bin',
          sizeBytes: 2097152,
          isValid: true,
          suggestedRegion: 'full',
        } as unknown as T;

      case 'select_file_native':
        return { selected: true, file_path: '/firmware/ME961_Stage1_v2.bin' } as unknown as T;

      case 'scanSerialPorts':
        return [
          { device: 'COM3', description: 'STN2120 OBDLink Adapter', manufacturer: 'SparkFun', likelyAdapter: true },
          { device: 'COM1', description: 'Communications Port', manufacturer: '(Standard port types)', likelyAdapter: false },
        ] as unknown as T;

      default:
        return { success: true } as unknown as T;
    }
  }
}

export const pyClient = new PyWebViewClient();
