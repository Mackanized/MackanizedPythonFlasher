/**
 * Normalized PyWebView Bridge Errors
 */

export class PyWebViewBridgeError extends Error {
  code: string;
  details?: Record<string, unknown>;

  constructor(code: string, message: string, details?: Record<string, unknown>) {
    super(message);
    this.name = 'PyWebViewBridgeError';
    this.code = code;
    this.details = details;
  }
}

export class HardwareConnectionError extends PyWebViewBridgeError {
  constructor(message: string, details?: Record<string, unknown>) {
    super('ERR_HARDWARE_CONNECTION', message, details);
    this.name = 'HardwareConnectionError';
  }
}

export class EcuCommunicationError extends PyWebViewBridgeError {
  constructor(message: string, details?: Record<string, unknown>) {
    super('ERR_ECU_COMMUNICATION', message, details);
    this.name = 'EcuCommunicationError';
  }
}

export class FirmwareValidationError extends PyWebViewBridgeError {
  constructor(message: string, details?: Record<string, unknown>) {
    super('ERR_FIRMWARE_VALIDATION', message, details);
    this.name = 'FirmwareValidationError';
  }
}

export class PreflightSafetyError extends PyWebViewBridgeError {
  constructor(message: string, details?: Record<string, unknown>) {
    super('ERR_PREFLIGHT_SAFETY', message, details);
    this.name = 'PreflightSafetyError';
  }
}
