import sys
from typing import Dict, Type

from adapters.j2534 import J2534Adapter, get_installed_j2534_devices
from adapters.base_adapter import BaseAdapter
from ecus.base_ecu import BaseECU
from ecus import Motronic961, Motronic96, Trionic8, EDC16C39, EDC17C19
from flasher import ECUFlasher
from logger import app_logger

KVASER_ERR_MSG = ""
try:
    from adapters.kvaser import KvaserAdapter
    HAS_KVASER = True
except Exception as e:
    HAS_KVASER = False
    KVASER_ERR_MSG = str(e)

ADAPTERS: Dict[str, Type[BaseAdapter]] = {}
if HAS_KVASER:
    ADAPTERS["1"] = ("Kvaser", KvaserAdapter)
ADAPTERS["2"] = ("J2534", J2534Adapter)

ECUS: Dict[str, Type[BaseECU]] = {
    "1": ("Bosch ME9.6.1", Motronic961),
    "2": ("Bosch ME9.6", Motronic96),
    "3": ("Trionic 8", Trionic8),
    "4": ("Bosch EDC16C39", EDC16C39),
    "5": ("Bosch EDC17C19", EDC17C19),
}


def choose_adapter() -> BaseAdapter:
    print("\nSelect CAN Adapter:")
    for key, (name, _) in ADAPTERS.items():
        print(f"  {key}: {name}")
    if not HAS_KVASER:
        print(f"  (Note: Kvaser unavailable: {KVASER_ERR_MSG}. Use '.venv\\Scripts\\python flasher_cli.py')")
    choice = input("Adapter choice: ").strip()
    if choice not in ADAPTERS:
        print("[FAIL] Invalid choice.")
        sys.exit(1)
    name, cls = ADAPTERS[choice]
    print(f"  Using {name}")

    if cls is J2534Adapter:
        devices = get_installed_j2534_devices()
        if not devices:
            print("[FAIL] No J2534 PassThru devices found in registry.")
            sys.exit(1)
        if len(devices) == 1:
            dll_path = devices[0]["dll"]
            print(f"  Using: {devices[0]['name']}")
        else:
            print("\n  Available J2534 devices:")
            for i, dev in enumerate(devices):
                print(f"    {i + 1}: {dev['name']}")
            dev_choice = input("  Device choice: ").strip()
            try:
                idx = int(dev_choice) - 1
                dll_path = devices[idx]["dll"]
                print(f"  Using: {devices[idx]['name']}")
            except (ValueError, IndexError):
                print("[FAIL] Invalid device choice.")
                sys.exit(1)
        return J2534Adapter(dll_path=dll_path)

    return cls(channel=0)


def choose_ecu() -> BaseECU:
    print("\nSelect ECU:")
    for key, (name, _) in ECUS.items():
        print(f"  {key}: {name}")
    choice = input("ECU choice: ").strip()
    if choice not in ECUS:
        print("[FAIL] Invalid choice.")
        sys.exit(1)
    name, cls = ECUS[choice]
    ecu = cls()
    print(f"  Using {ecu.NAME}")
    return ecu


def choose_region(ecu: BaseECU, for_write: bool = False) -> str:
    regions = ecu.get_write_regions() if for_write else ecu.get_flash_regions()
    label = "Write" if for_write else "Read"
    print(f"\nSelect Region ({label}):")
    for i, (name, (start, end, _)) in enumerate(regions.items(), 1):
        size_kb = (end - start) / 1024
        print(f"  {i}: {name} (0x{start:06X} - 0x{end:06X}, {size_kb:.0f} KB)")
    choice = input("Region choice: ").strip()
    keys = list(regions.keys())
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(keys):
            return keys[idx]
    except ValueError:
        pass
    if choice in regions:
        return choice
    print("[FAIL] Invalid choice.")
    sys.exit(1)


def choose_operation() -> str:
    print("\nSelect Operation:")
    print("  1: Read ECU")
    print("  2: Write ECU")
    print("  3: ECU Info")
    choice = input("Operation choice: ").strip()
    return choice


def main():
    print("=" * 50)
    print("  ECU Flasher - Modular GMLAN Flash Tool")
    print("=" * 50)

    adapter = choose_adapter()
    ecu = choose_ecu()

    print("\n" + "-" * 50)
    print("  Ready to connect to ECU")
    print("  - Turn ignition ON (dashboard lights on)")
    print("  - Connect the OBD cable to the vehicle")
    print("  - Ensure the ECU is powered and awake")
    print("-" * 50)
    input("  Press Enter when ready...")

    flasher = ECUFlasher(adapter, ecu)
    if not flasher.connect():
        print("[FAIL] Could not connect to adapter.")
        print("       Check that the device is plugged in and drivers are installed.")
        return

    try:
        op = choose_operation()

        if op == "3":
            print("\nReading ECU information...")
            info = flasher.read_ecu_info()
            labels = {
                "vin": "VIN",
                "serial": "Serial number",
                "diag_address": "Diagnostic address",
                "programming_date": "Programming date",
                "end_pn": "End model partnumber",
                "base_pn": "Base model partnumber",
                "main_os": "Main OS",
                "engine_calib": "Engine Calib",
                "system_calib": "System Calib",
                "speedo_calib": "Speedo Calib",
                "calibration_set": "Calibration set",
                "codefile_version": "Codefile version",
                "diag_data_id": "Diag Data Identifier",
                "mfg_enable_counter": "Mfg Enable Counter",
                "tester_serial": "Tester Serial",
                "bosch_enable_counter": "Bosch Enable Counter",
                "top_speed": "Speed limiter",
                "radum": "Radum",
                "pmc_w": "Pmc w",
            }
            print("\n" + "=" * 50)
            print(f"  ECU: {ecu.NAME}")
            print("=" * 50)
            for key in ecu.get_info_pids():
                val = info.get(key, "?")
                label = labels.get(key, key)
                print(f"  {label:25s} {val}")
            print("=" * 50)
            return

        if op == "1":
            region = choose_region(ecu, for_write=False)
            _, _, default_file = ecu.get_flash_regions()[region]
            print(f"\nStarting read ({region})...")
            filename = flasher.read_to_file(region)
            print(f"\n  [OK] Saved to: {filename}")

        elif op == "2":
            region = choose_region(ecu, for_write=True)
            _, _, default_file = ecu.get_write_regions()[region]
            filename = input(f"Input filename [{default_file}]: ").strip()
            if not filename:
                filename = default_file
            print(f"\nStarting write ({region})...")
            if flasher.write_from_file(region, filename):
                print("\n  [OK] Flash complete. ECU reset.")
            else:
                print("\n  [FAIL] Write failed. Check flasher.log.")

        else:
            print("[FAIL] Invalid operation.")

    except TimeoutError:
        print("\n[FAIL] ECU timeout. Check connections.")
        app_logger.error("ECU timeout during operation.")
    except Exception as e:
        print(f"\n[FAIL] {e}")
        app_logger.error(f"Unexpected error: {e}")
    finally:
        flasher.disconnect()
        print("Done.")


if __name__ == "__main__":
    main()
