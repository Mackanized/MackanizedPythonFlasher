"""
End-to-end verification script for Bosch ME9.6.1:
1. Program ECU calibration region (0x1C2000 - 0x1F0000) from ME961_Calibration_Backup.bin
2. Read back calibration region (0x1C2000 - 0x1F0000) into ME961_Calibration_Read.bin
3. Perform a byte-by-byte comparison between original and read binary files for verification.
"""
import sys
import os
import time
from adapters.kvaser import KvaserAdapter
from ecus.motronic961 import Motronic961
from flasher import ECUFlasher
from logger import app_logger

def main():
    original_bin = "ME961_Calibration_Backup.bin"
    read_bin = "ME961_Calibration_Read.bin"

    if not os.path.exists(original_bin):
        print(f"[ERROR] Original binary file '{original_bin}' not found.")
        sys.exit(1)

    print("==================================================")
    print("  Bosch ME9.6.1 Calibration Program & Verify Test")
    print("==================================================")
    print(f"Target ECU   : Bosch ME9.6.1")
    print(f"CAN Adapter  : Kvaser (Channel 0 @ 500kbps)")
    print(f"Write File   : {original_bin}")
    print(f"Read File    : {read_bin}")
    print(f"Write Region : calibration (0x1C2000 - 0x1F0000, 184 KB)")
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
        # STEP 1: Program ECU calibration
        with open(original_bin, "rb") as f:
            orig_raw = f.read()

        start_addr = 0x1C2000
        end_addr = 0x1F0000
        orig_calib_bytes = orig_raw[start_addr:end_addr]

        print("\n--- STEP 1: Programming ECU Calibration ---")
        t_start = time.time()
        write_ok = flasher.write_region(start_addr, end_addr, orig_calib_bytes, max_retries=3)
        t_write = time.time() - t_start

        if not write_ok:
            print(f"\n[FAIL] Calibration programming failed after {t_write:.1f}s.")
            sys.exit(1)

        print(f"\n[SUCCESS] Calibration programming completed in {t_write:.1f}s!")

        # Pause briefly before reading
        time.sleep(1.0)

        # STEP 2: Read ECU calibration to NEW file
        print("\n--- STEP 2: Reading ECU Calibration to NEW file ---")
        t_start = time.time()
        read_image = flasher.read_region(start_addr, end_addr)
        t_read = time.time() - t_start

        read_calib_bytes = bytes(read_image[start_addr:end_addr])

        with open(read_bin, "wb") as f:
            f.write(read_calib_bytes)

        print(f"\n[SUCCESS] Calibration read completed in {t_read:.1f}s!")
        print(f"Saved read calibration bytes ({len(read_calib_bytes)} bytes) to: {read_bin}")

        # STEP 3: Perform byte-by-byte binary verification
        print("\n--- STEP 3: Binary Verification (Byte-by-Byte Compare) ---")
        print(f"Original slice size: {len(orig_calib_bytes)} bytes")
        print(f"Read slice size    : {len(read_calib_bytes)} bytes")

        if len(orig_calib_bytes) != len(read_calib_bytes):
            print("[FAIL] Size mismatch between original slice and read data!")
            sys.exit(1)

        mismatches = []
        for i in range(len(orig_calib_bytes)):
            if orig_calib_bytes[i] != read_calib_bytes[i]:
                addr = start_addr + i
                mismatches.append((addr, orig_calib_bytes[i], read_calib_bytes[i]))

        if not mismatches:
            print("\n==================================================")
            print("  🎉 VERIFICATION PASSED! 100% BYTE-EXACT MATCH!")
            print(f"  All {len(orig_calib_bytes)} bytes match perfectly!")
            print("==================================================")
            sys.exit(0)
        else:
            pct_match = ((len(orig_calib_bytes) - len(mismatches)) / len(orig_calib_bytes)) * 100
            print(f"\n[FAIL] Found {len(mismatches)} mismatched byte(s) out of {len(orig_calib_bytes)} ({pct_match:.2f}% match).")
            print("First 10 mismatches:")
            for addr, b_orig, b_read in mismatches[:10]:
                print(f"  Addr 0x{addr:06X}: Original 0x{b_orig:02X} != Read 0x{b_read:02X}")
            sys.exit(1)

    finally:
        flasher.disconnect()

if __name__ == "__main__":
    main()
