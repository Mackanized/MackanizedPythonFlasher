"""
Non-interactive test script to execute Bosch ME9.6.1 calibration write via Kvaser adapter.
Allows automated testing via terminal commands without user prompts.
"""
import sys
import os
import time
from adapters.kvaser import KvaserAdapter
from ecus.motronic961 import Motronic961
from flasher import ECUFlasher
from logger import app_logger

def main():
    bin_file = "ME961_Calibration_Backup.bin"
    if not os.path.exists(bin_file):
        print(f"[ERROR] Backup binary file '{bin_file}' not found.")
        sys.exit(1)

    print("==================================================")
    print("  Automated Non-Interactive ECU Flasher Test")
    print("==================================================")
    print(f"Target ECU : Bosch ME9.6.1")
    print(f"CAN Adapter: Kvaser (Channel 0 @ 500kbps)")
    print(f"Write File : {bin_file}")
    print(f"Write Region: calibration (0x1C2000 - 0x1F0000)")
    print("==================================================")

    adapter = KvaserAdapter(channel=0)
    ecu = Motronic961()

    def progress_callback(pct: float, msg: str):
        print(f"[Progress] {pct:5.1f}% | {msg}")

    flasher = ECUFlasher(adapter, ecu, progress_callback=progress_callback)

    print("\nConnecting adapter...")
    if not flasher.connect():
        print("[FAIL] Adapter connection failed.")
        sys.exit(1)

    try:
        with open(bin_file, "rb") as f:
            data = f.read()

        start_time = time.time()
        print("\nStarting calibration write (0x1C2000 - 0x1F0000)...")
        success = flasher.write_region(0x1C2000, 0x1F0000, data, max_retries=3)
        elapsed = time.time() - start_time

        if success:
            print(f"\n[SUCCESS] Calibration write completed in {elapsed:.1f} seconds!")
            sys.exit(0)
        else:
            print(f"\n[FAIL] Calibration write failed after {elapsed:.1f} seconds. Check flasher.log.")
            sys.exit(1)
    finally:
        flasher.disconnect()

if __name__ == "__main__":
    main()
