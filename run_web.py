#!/usr/bin/env python3
"""
Mackanized flasher - Desktop Web Suite Runner & PyWebView API Gateway

Launches the hyper-polished 2026 Web Suite for Mackanized flasher.
Bridges Python backend services (ECU Registry, Flasher Engine, Telemetry) directly to the web interface.
"""

import http.server
import json
import os
import socketserver
import sys
import threading
import tempfile
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, List

from application.services.flasher_service import FlasherService
from application.state.app_state import ApplicationState
from ecus.registry import EcuRegistry
from gui.qt_startup import is_non_gui_automation, qt_startup_error
from infrastructure.settings import SettingsManager
from infrastructure.telemetry import TelemetryEngine
from adapters.mock_adapter import MockAdapter
from adapters.j2534 import get_installed_j2534_devices
from adapters.kvaser import HAS_KVASER
from logger import configure_logging

PORT = 8080
WEB_DIST_DIR = Path(__file__).parent / "web" / "dist"


class PythonApiBridge:
    """Central JS-Python PyWebView Gateway API Bridge."""

    def __init__(self, flasher: FlasherService, telemetry: TelemetryEngine, state: ApplicationState):
        self._flasher = flasher
        self._telemetry = telemetry
        self._state = state
        self._settings = SettingsManager()
        self._flasher.disable_preflight = self._settings.disable_preflight

    def getAdapters(self) -> List[Dict[str, Any]]:
        return [
            {"id": "mock", "name": "MockAdapter (Offline Simulator)", "type": "mock", "isAvailable": True},
            {"id": "kvaser", "name": "Kvaser CAN (CANlib API)", "type": "kvaser", "isAvailable": HAS_KVASER},
            {"id": "j2534", "name": "J2534 PassThru (DLL)", "type": "j2534", "isAvailable": bool(get_installed_j2534_devices())},
        ]

    def connectAdapter(self, adapter_id: str) -> bool:
        print(f"[Backend API] Connecting adapter: {adapter_id}")
        if not self._flasher.set_adapter(adapter_id, self._settings.j2534_dll_path):
            return False
        res = self._flasher.connect_adapter()
        if res:
            self._settings.default_adapter_key = adapter_id
        return res

    def disconnectAdapter(self) -> bool:
        print("[Backend API] Disconnecting adapter")
        return self._flasher.disconnect_adapter()

    def isConnected(self) -> bool:
        return self._flasher.is_connected

    def getTelemetry(self) -> Dict[str, Any]:
        payload = self._telemetry.get_snapshot()
        adapter = self._flasher.adapter
        if self._flasher.is_connected and adapter.is_simulation:
            voltage = getattr(adapter, "supply_voltage", None)
            payload["voltage"] = voltage
            payload["voltage_status"] = "normal" if voltage is not None and voltage >= 12.4 else "unknown"
        return payload

    def getRegisteredEcus(self) -> List[Dict[str, str]]:
        return [
            {
                "id": key,
                "name": name,
                "developmentStatus": EcuRegistry.instantiate(key).CAPABILITIES.development_status,
            }
            for key, name in EcuRegistry.list_ecus()
        ]

    def setSelectedEcu(self, ecu_id: str) -> Dict[str, Any]:
        ecu_inst = EcuRegistry.instantiate(ecu_id)
        if not self._flasher.set_ecu(ecu_inst, ecu_id):
            raise RuntimeError("ECU selection is locked during an active operation.")
        print(f"[Backend API] Selected ECU: {ecu_inst.NAME} [{ecu_id}]")
        if self._flasher.is_connected:
            return self.readEcuInfo()
        ecu = self._flasher.ecu
        return {
            "name": ecu.NAME,
            "vehicle": "Not identified",
            "hardwareNo": "Connect to identify",
            "softwareNo": "Connect to identify",
            "mcu": getattr(ecu, "mcu", "Not declared"),
            "protocol": "GMLAN over ISO-TP",
            "securityAlgo": f"SecurityAccess level 0x{ecu.SECURITY_LEVEL:02X}",
            "flashSizeKb": ecu.TOTAL_FLASH_SIZE // 1024,
            "eepromSizeKb": getattr(ecu, "eeprom_size_kb", 0),
            "isSimulation": self._flasher.adapter.is_simulation,
            **self._capability_payload(ecu),
        }

    def readEcuInfo(self) -> Dict[str, Any]:
        ecu = self._flasher.ecu
        info = self._flasher.read_connected_ecu_info()
        return {
            "name": ecu.NAME,
            "vehicle": getattr(ecu, "vehicle", "Unknown / simulator definition"),
            "hardwareNo": info.get("hardware_type", info.get("base_pn", "Unknown")),
            "softwareNo": info.get("main_os", "Unknown"),
            "mcu": getattr(ecu, "mcu", "Not declared"),
            "protocol": "GMLAN over ISO-TP",
            "securityAlgo": f"SecurityAccess level 0x{ecu.SECURITY_LEVEL:02X}",
            "flashSizeKb": ecu.TOTAL_FLASH_SIZE // 1024,
            "eepromSizeKb": getattr(ecu, "eeprom_size_kb", 0),
            "vin": info.get("vin", "Unknown"),
            "isSimulation": self._flasher.adapter.is_simulation,
            **self._capability_payload(ecu),
        }

    def _capability_payload(self, ecu) -> Dict[str, Any]:
        from domain.physical_write_readiness import assess_physical_write_readiness

        simulation = self._flasher.adapter.is_simulation
        write_regions = ecu.get_simulation_write_regions() if simulation else ecu.get_write_regions()
        readiness = assess_physical_write_readiness(ecu)
        return {
            "supportsRead": simulation or ecu.CAPABILITIES.supports_full_read or ecu.CAPABILITIES.supports_calibration_read,
            "supportsWrite": simulation or readiness.ready,
            "supportsRecovery": ecu.CAPABILITIES.supports_recovery,
            "developmentStatus": ecu.CAPABILITIES.development_status,
            "physicalWriteReadiness": readiness.as_dict(),
            "readRegions": list(ecu.get_flash_regions()),
            "writeRegions": list(write_regions),
        }

    def selectCalibrationFile(self, region: str = "calibration") -> Dict[str, Any]:
        """Open native desktop file dialog using PyWebView native host."""
        try:
            import webview
            if len(webview.windows) > 0:
                window = webview.windows[0]
                dialog_type = getattr(getattr(webview, 'FileDialog', None), 'OPEN', getattr(webview, 'OPEN_DIALOG', 10))
                result = window.create_file_dialog(
                    dialog_type,
                    file_types=('Raw Binary Files (*.bin)', 'All Files (*.*)')
                )
                if result and len(result) > 0:
                    path = result[0]
                    self._settings.add_recent_file(path)
                    filename = os.path.basename(path)
                    file_size = os.path.getsize(path)
                    suggested = self._flasher.ecu.suggest_region_for_file_size(
                        file_size, is_simulation=self._flasher.adapter.is_simulation
                    )
                    return {
                        "path": path,
                        "filename": filename,
                        "sizeBytes": file_size,
                        "isValid": True,
                        "suggestedRegion": suggested,
                    }
        except (ImportError, OSError, RuntimeError) as e:
            print(f"[Backend API File Dialog Error] {e}")

        # Fallback sample binary generation if native file dialog is unavailable or cancelled
        regions = (
            self._flasher.ecu.get_simulation_write_regions()
            if self._flasher.adapter.is_simulation
            else self._flasher.ecu.get_write_regions()
        )
        if region not in regions:
            region = next(iter(regions), "full")
        start, end, _ = regions.get(region, (0, self._flasher.ecu.TOTAL_FLASH_SIZE, ""))
        size = end - start
        pattern = bytes(((i * 29 + 0x5A) & 0xFF) for i in range(256))
        data = (pattern * ((size + 255) // 256))[:size]
        path = Path(tempfile.gettempdir()) / f"Mackanized flasher_sample_{region}_{size}.bin"
        path.write_bytes(data)
        self._settings.add_recent_file(str(path))
        suggested = self._flasher.ecu.suggest_region_for_file_size(
            size, is_simulation=self._flasher.adapter.is_simulation
        )
        return {
            "path": str(path),
            "filename": path.name,
            "sizeBytes": size,
            "isValid": True,
            "isSimulation": True,
            "suggestedRegion": suggested,
        }

    def getRecentFiles(self) -> List[str]:
        return self._settings.recent_files

    def getSettings(self) -> Dict[str, Any]:
        return {
            "theme": self._settings.theme,
            "densityMode": self._settings.density_mode,
            "defaultAdapter": self._settings.default_adapter_key,
            "j2534Dll": self._settings.j2534_dll_path,
            "baudrate": self._settings.baudrate,
            "disablePreflight": self._settings.disable_preflight,
        }

    def updateSettings(self, settings_dict: Dict[str, Any]) -> bool:
        if "theme" in settings_dict:
            self._settings.theme = settings_dict["theme"]
        if "densityMode" in settings_dict:
            self._settings.density_mode = settings_dict["densityMode"]
        if "defaultAdapter" in settings_dict:
            self._settings.default_adapter_key = settings_dict["defaultAdapter"]
        if "j2534Dll" in settings_dict:
            self._settings.j2534_dll_path = settings_dict["j2534Dll"]
        if "baudrate" in settings_dict:
            self._settings.baudrate = int(settings_dict["baudrate"])
        if "disablePreflight" in settings_dict:
            self._settings.disable_preflight = bool(settings_dict["disablePreflight"])
            self._flasher.disable_preflight = self._settings.disable_preflight
        return True

    def startFlashRead(self, region: str = "full") -> Dict[str, Any]:
        print(f"[Backend API] Starting Flash Read region: {region}")
        accepted = self._flasher.start_read_operation(region)
        status = self._flasher.get_operation_status()
        return {"accepted": accepted, "operationId": status["operationId"] if accepted else ""}

    def startFlashWrite(
        self,
        file_path: str,
        region: str = "full",
        operator_confirmed: bool = False,
        backup_verified: bool = False,
    ) -> Dict[str, Any]:
        print(f"[Backend API] Starting Flash Write file: {file_path}, region: {region}")
        if not operator_confirmed:
            print("[Backend API] Write rejected: operator confirmation missing")
            return {"accepted": False, "operationId": ""}
        if file_path:
            self._settings.add_recent_file(file_path)
        accepted = self._flasher.start_write_operation(
            file_path,
            region,
            operator_confirmed=operator_confirmed,
            backup_verified=backup_verified,
        )
        status = self._flasher.get_operation_status()
        return {"accepted": accepted, "operationId": status["operationId"] if accepted else ""}

    def startRecoveryFlash(
        self,
        operator_confirmed: bool = False,
        backup_verified: bool = False,
    ) -> Dict[str, Any]:
        print("[Backend API] Starting T8 recovery session/loader preparation")
        if not operator_confirmed:
            print("[Backend API] Recovery rejected: operator confirmation missing")
            return {"accepted": False, "operationId": ""}
        accepted = self._flasher.start_recovery_operation(
            operator_confirmed=operator_confirmed,
            backup_verified=backup_verified,
        )
        status = self._flasher.get_operation_status()
        return {"accepted": accepted, "operationId": status["operationId"] if accepted else ""}

    def getOperationStatus(self) -> Dict[str, Any]:
        return self._flasher.get_operation_status()

    def emergencyStop(self) -> bool:
        print("[Backend API] EMERGENCY STOP ACTIVATED")
        return self._flasher.cancel_operation()

    def readDtcs(self) -> List[Dict[str, Any]]:
        if not self._flasher.is_connected:
            raise RuntimeError("Connect to an ECU before reading DTCs.")
        adapter = self._flasher.adapter
        if not isinstance(adapter, MockAdapter):
            raise RuntimeError("Hardware DTC reading is not implemented for the selected protocol strategy.")
        return [
            {"code": code, "description": description, "status": status, "severity": severity}
            for code, description, status, severity in adapter.read_simulated_dtcs()
        ]

    def clearDtcs(self) -> bool:
        if not self._flasher.is_connected:
            return False
        adapter = self._flasher.adapter
        if not isinstance(adapter, MockAdapter):
            return False
        adapter.clear_simulated_dtcs()
        return True

    def exportCanTrace(self, target_format: str = "asc") -> Dict[str, Any]:
        """Export active CAN trace log to ASC or CSV format."""
        from infrastructure.can_logger import CANLogger
        import tempfile
        logger = CANLogger()
        suffix = ".asc" if target_format == "asc" else ".csv"
        target_path = Path(tempfile.gettempdir()) / f"pythonflasher_trace_{int(time.time())}{suffix}"
        if target_format == "asc":
            logger.export_vector_asc(str(target_path))
        else:
            logger.export_csv(str(target_path))
        return {"success": True, "path": str(target_path)}


class SinglePageApplicationHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIST_DIR), **kwargs)

    def do_GET(self):
        target_path = WEB_DIST_DIR / self.path.lstrip("/")
        if not target_path.exists() and not self.path.startswith("/assets/"):
            self.path = "/index.html"
        return super().do_GET()


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def find_available_server(start_port=8080):
    for port in range(start_port, start_port + 20):
        try:
            httpd = ReusableTCPServer(("127.0.0.1", port), SinglePageApplicationHandler)
            return httpd, port
        except OSError:
            continue
    raise RuntimeError("Could not find an available HTTP port between 8080 and 8100.")


def main():
    configure_logging()
    if not WEB_DIST_DIR.exists():
        print(f"Error: Web build artifacts not found at {WEB_DIST_DIR}")
        print("Run 'cd web && npm run build' first.")
        sys.exit(1)

    if is_non_gui_automation():
        print(qt_startup_error())
    else:
        try:
            from PySide6.QtWidgets import QApplication
            if not QApplication.instance():
                _qapp = QApplication(sys.argv)
        except (ImportError, RuntimeError) as exc:
            print(f"Qt host initialization unavailable: {exc}")

    app_state = ApplicationState()
    flasher = FlasherService(app_state)
    telemetry = TelemetryEngine(adapter_provider=lambda: flasher.adapter)
    
    api_bridge = PythonApiBridge(flasher, telemetry, app_state)
    telemetry.start_monitoring()

    httpd, active_port = find_available_server(PORT)

    print("============================================================")
    print("⚡ Mackanized flasher - Next-Gen Modern Desktop Suite")
    print("============================================================")
    print(f"Serving web application at: http://127.0.0.1:{active_port}")

    try:
        import webview
        print("Launching native desktop window (PyWebView)...")
        
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        def on_closing():
            if flasher.operation_active:
                print("[Desktop Window] Intercepted close request: Active ECU operation in progress!")
                return False  # Prevent window close during active write
            telemetry.stop_monitoring()
            flasher.disconnect_adapter()
            print("[Desktop Window] Clean desktop shutdown complete.")
            return True

        window = webview.create_window(
            "Mackanized flasher - OEM Desktop Suite",
            f"http://127.0.0.1:{active_port}",
            js_api=api_bridge,
            width=1280,
            height=800,
            min_size=(1024, 720)
        )
        window.events.closing += on_closing
        webview.start()
    except ImportError:
        print("PyWebView not installed. Opening in default web browser...")
        webbrowser.open(f"http://127.0.0.1:{active_port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
