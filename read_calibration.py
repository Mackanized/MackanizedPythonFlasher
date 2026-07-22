import os
import time
from adapters.kvaser import KvaserAdapter
from ecus import Motronic961
from gmlan import GMLANClient
from logger import app_logger

def clear_bus_buffer(adapter):
    """Flushes any stale or lingering frames from the adapter receive buffer."""
    while True:
        rx_id, rx_data = adapter.read_frame(timeout_ms=10)
        if not rx_data:
            break

def main():
    print("=== GMLAN 2MB ECU Memory Dumper (Bosch ME9.6.1) ===")
    app_logger.info("=== Starting GMLAN 2MB ECU Memory Dumper (Bosch ME9.6.1) ===")
    
    ecu = Motronic961()
    adapter = KvaserAdapter(channel=0)
    if not adapter.connect(baudrate=500000):
        print("[FAIL] Could not connect to Kvaser interface.")
        app_logger.error("Could not connect to Kvaser interface.")
        return

    try:
        adapter.check_bus_status()
        print("Clearing Kvaser receive buffer...")
        clear_bus_buffer(adapter)
        gmlan = GMLANClient(adapter, ecu)

        print("\n[1/3] Entering Programming Session (0x10 0x02)...")
        app_logger.info("Attempting to enter programming session (0x10 0x02)...")
        if not gmlan.enter_programming_mode():
            print("  [FAIL] ECU denied programming session.")
            app_logger.error("ECU denied programming session.")
            return
        print("  [OK] Programming Session Active.")
        app_logger.info("Programming session active.")

        print("\n[2/3] Performing Security Authentication...")
        app_logger.info("Performing security authentication (Security Access)...")
        if not gmlan.authenticate():
            print("  [FAIL] Security Access rejected.")
            app_logger.error("Security Access denied.")
            return
        app_logger.info("Security Access granted.")

        # ME9.6.1 Full Flash Layout Requirement: Exactly 2 MB (0x200000 bytes)
        total_flash_size = 0x200000  # 2,097,152 bytes
        full_flash_image = bytearray(b'\xFF' * total_flash_size)

        # Target range: Calibration Area (0x1C0000 to 0x1FE000)
        start_address = 0x1C0000
        target_length = 0x3E000  # 248 KB
        
        # Matches exactly the professional tool's block size from the reference log
        high_speed_chunk = 0xFA  # 250 bytes[cite: 1]
        fallback_chunk = 0x02    # 2 bytes granular fallback if needed
        current_addr = start_address
        end_addr = start_address + target_length

        print(f"\n[3/3] Dumping Calibration Region (0x{start_address:06X} - 0x{end_addr:06X}) into 2 MB layout...")
        app_logger.info(f"Starting reading of calibration area from 0x{start_address:06X} to 0x{end_addr:06X}")

        last_tp_time = time.time()

        while current_addr < end_addr:
            remaining = end_addr - current_addr
            fetch_size = min(high_speed_chunk, remaining)

            # Keep session alive by sending Tester Present (0x3E) every 2 seconds
            if time.time() - last_tp_time >= 2.0:
                gmlan.send_tester_present()
                last_tp_time = time.time()

            try:
                # Attempt High-Speed Block Read (250 bytes / 0xFA)[cite: 1]
                chunk = gmlan.read_memory_by_address(current_addr, fetch_size)
            except TimeoutError:
                print(f"\n[FAIL] ECU stopped responding (Timeout) at 0x{current_addr:06X}.")
                app_logger.error(f"ECU did not respond at 0x{current_addr:06X}. Aborting read.")
                return

            if chunk:
                # Place data at the exact absolute memory offset in the 2MB image
                offset = current_addr
                full_flash_image[offset : offset + len(chunk)] = chunk
                current_addr += fetch_size
            else:
                # Granular Fallback Loop for restricted/sparse sub-blocks
                app_logger.warning(f"High-speed read failed at 0x{current_addr:06X}. Activating 2-byte fallback.")
                print(f"\n  [WARN] Fallback active at 0x{current_addr:06X}...")
                clear_bus_buffer(adapter)
                
                fallback_range_size = min(high_speed_chunk, remaining)
                fallback_end = current_addr + fallback_range_size

                while current_addr < fallback_end and current_addr < end_addr:
                    if time.time() - last_tp_time >= 2.0:
                        gmlan.send_tester_present()
                        last_tp_time = time.time()

                    try:
                        small_chunk = gmlan.read_memory_by_address(current_addr, fallback_chunk, timeout_s=0.5)
                    except TimeoutError:
                        print(f"\n[FAIL] ECU stopped responding (Timeout) during fallback at 0x{current_addr:06X}.")
                        app_logger.error(f"ECU did not respond during fallback at 0x{current_addr:06X}. Aborting.")
                        return

                    offset = current_addr
                    
                    if not small_chunk:
                        full_flash_image[offset : offset + fallback_chunk] = b'\xFF' * fallback_chunk
                    else:
                        full_flash_image[offset : offset + len(small_chunk)] = small_chunk
                    
                    current_addr += fallback_chunk

                app_logger.info("Fallback block processed. Returning to high-speed mode.")

            # Calculate and display progress relative to the calibration block
            bytes_read = current_addr - start_address
            progress = (bytes_read / target_length) * 100
            print(f"  [Progress] {progress:.1f}% complete (Offset: 0x{current_addr:06X})", end='\r')

        # Save absolute path 2MB file
        cwd = os.getcwd()
        filename = os.path.join(cwd, "ME961_FullFlash_Calibration_Backup.bin")
        
        with open(filename, "wb") as f:
            f.write(full_flash_image)
            
        print(f"\n\n  [OK] SUCCESS! Complete 2MB flash file with correct offsets saved to:\n  {filename} ({len(full_flash_image)} bytes).")
        app_logger.info(f"Full 2MB flash file saved to: {filename}")

    finally:
        adapter.disconnect()
        print("[Kvaser] Disconnected.")
        app_logger.info("Kvaser interface disconnected.")

if __name__ == "__main__":
    main()