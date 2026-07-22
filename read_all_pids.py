"""
Read all known GMLAN PIDs from the ECU and print results.
Useful for discovering which PIDs are supported by a specific ECU.
"""
import time
from adapters.kvaser import KvaserAdapter
from ecus.motronic961 import Motronic961
from gmlan import GMLANClient
from logger import app_logger

ALL_PIDS = [
    (0x02, "Speed limiter",        "speed16"),
    (0x08, "Software version",     "ascii"),
    (0x0A, "Build date",           "ascii"),
    (0x24, "Radum",                "byte"),
    (0x2E, "Pmc w",                "speed16"),
    (0x29, "RPM limiter",          "speed16"),
    (0x25, "Oil quality",          "byte"),
    (0x70, "Bosch Enable Counter", "hexbyte"),
    (0x71, "Hardware",             "ascii"),
    (0x72, "ECU description",      "ascii"),
    (0x73, "Codefile version",     "ascii"),
    (0x74, "Calibration set",      "ascii"),
    (0x90, "VIN",                  "ascii"),
    (0x92, "Supplier ID",          "ascii"),
    (0x95, "SW number",            "ascii"),
    (0x97, "Hardware type",        "ascii"),
    (0x98, "Tester Serial",        "ascii"),
    (0x99, "Programming date",     "hexdate"),
    (0x9A, "Diag Data Identifier", "diagid"),
    (0xA0, "Mfg Enable Counter",   "byte"),
    (0xB0, "Diagnostic address",   "hexbyte"),
    (0xB4, "Serial number",        "ascii"),
    (0xC1, "Main OS",              "partnum"),
    (0xC2, "Engine Calib",         "partnum"),
    (0xC3, "System Calib",         "partnum"),
    (0xC4, "Speedo Calib",         "partnum"),
    (0xC5, "Slave OS",             "partnum"),
    (0xC6, "SW identifier 6",      "partnum"),
    (0x7C, "Saab partnumber",      "partnum"),
    (0xCB, "End model partnumber", "partnum"),
    (0xCC, "Base model partnumber","partnum"),
]


def decode(pid: int, data: bytes, fmt: str) -> str:
    if not data:
        return "—"
    try:
        if fmt == "ascii":
            return data.decode('ascii', errors='ignore').strip('\x00 ').strip()
        elif fmt == "byte":
            return str(data[0])
        elif fmt == "hexbyte":
            return f"0x{data[0]:02X}"
        elif fmt == "speed16":
            if len(data) >= 2:
                return f"{((data[0] << 8) | data[1]) / 10:.1f}"
            return "—"
        elif fmt == "hexdate":
            if len(data) >= 4:
                return f"{int.from_bytes(data[:4], 'big'):X}"
            return "—"
        elif fmt == "diagid":
            if len(data) >= 2:
                return f"0x{data[0]:02X} 0x{data[1]:02X}"
            return "—"
        elif fmt == "partnum":
            if len(data) >= 4:
                val = int.from_bytes(data[:4], 'big')
                return str(val) if val != 0 else "0"
            return "—"
        else:
            return data.hex().upper()
    except Exception as e:
        return f"<error: {e}>"


def main():
    adapter = KvaserAdapter()
    ecu = Motronic961()
    if not adapter.connect(baudrate=500000):
        print("Failed to connect adapter.")
        return

    adapter.check_bus_status()
    while adapter.read_frame(timeout_ms=10)[1]:
        pass

    gmlan = GMLANClient(adapter, ecu)

    print("Waking up ECU...")
    gmlan.wakeup_bus()
    time.sleep(0.1)

    print("Entering programming session...")
    if not gmlan.enter_programming_mode():
        print("Failed to enter programming session.")
        adapter.disconnect()
        return

    print(f"\n{'PID':<6} {'Name':<25} {'Value'}")
    print("-" * 70)

    for pid, name, fmt in ALL_PIDS:
        data = gmlan.read_data_by_identifier(pid, timeout_s=3.0)
        value = decode(pid, data, fmt)
        status = "OK" if data else "TIMEOUT"
        print(f"0x{pid:02X}  {name:<25} {value:<30} [{status}]")

    print("-" * 70)
    gmlan.return_to_normal_mode()
    adapter.disconnect()
    print("\nDone.")


if __name__ == "__main__":
    main()