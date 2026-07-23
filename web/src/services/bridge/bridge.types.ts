/**
 * Strict Typed Contract for PyWebView Bridge Communication
 */

export interface BridgeResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface AdapterDto {
  id: string;
  name: string;
  type: 'j2534' | 'kvaser' | 'stn' | 'socketcan' | 'mock';
  channel: number;
  available: boolean;
  dll_path?: string;
}

export interface EcuIdentityDto {
  ecu_family: string;
  display_name: string;
  vin: string;
  hardware_type: string;
  software_id: string;
  supplier: string;
  diag_address: string;
  programming_date: string;
  raw_pids: Record<string, string>;
}

export interface ConnectionStatusDto {
  connected: boolean;
  adapter_name: string;
  baudrate: number;
  ecu_family: string;
  battery_voltage: number;
  security_access: boolean;
  active_session: string;
}

export interface MemoryRegionDto {
  name: string;
  start_address: number;
  end_address: number;
  size_bytes: number;
  filename: string;
  readable: boolean;
  writable: boolean;
  protected: boolean;
}

export interface MemoryMapDto {
  ecu_name: string;
  total_flash_size: number;
  regions: MemoryRegionDto[];
}

export interface FileValidationDto {
  valid: boolean;
  file_name: string;
  file_size: number;
  detected_format: string;
  target_compatible: boolean;
  software_id_match: boolean;
  checksum_valid: boolean;
  checksum_name: string;
  calculated_checksum: string;
  warnings: string[];
  errors: string[];
  suggested_region: string;
}

export interface FlashProgressEvent {
  operation_id: string;
  phase: 'idle' | 'preparing' | 'erasing' | 'transferring' | 'verifying' | 'resetting' | 'completed' | 'failed' | 'cancelled';
  current_bytes: number;
  total_bytes: number;
  percentage: number;
  transfer_rate_kbps: number;
  elapsed_seconds: number;
  remaining_seconds: number;
  current_region: string;
  battery_voltage: number;
  message: string;
}

export interface DiagnosticDtcDto {
  code: string;
  status: 'active' | 'stored' | 'pending' | 'history';
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  raw_status_byte: string;
  freeze_frame?: Record<string, string>;
}

export interface TelemetrySignalDto {
  id: string;
  name: string;
  group: string;
  value: number;
  unit: string;
  min_value?: number;
  max_value?: number;
  timestamp: number;
}

export interface TraceLogEvent {
  id: string;
  timestamp: string;
  direction: 'TX' | 'RX' | 'INFO' | 'WARN' | 'ERROR';
  can_id: string;
  data: string;
  description: string;
}

export interface ProjectDto {
  id: string;
  name: string;
  created_at: string;
  last_modified: string;
  ecu_family: string;
  vin: string;
  calibration_file?: string;
  notes: string;
}
