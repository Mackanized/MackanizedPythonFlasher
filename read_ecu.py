import os
import sys
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
    choice = None
    if len(sys.argv) > 1:
        choice = sys.argv[1].strip()

    if not choice:
        print("=== GMLAN ECU Memory Utility (Bosch ME9.6.1) ===")
        print("Select Option:")
        print("  1: Engine Calibration Read (0x1C2000 - 0x200000, 248 KB, ~1.5 min)")
        print("  2: Full ECU Read (0x000000 - 0x200000, 2 MB, ~13 min)")
        print("  3: Engine Calibration Write (0x1C2000 - 0x200000, 248 KB, ~1.5 min)")
        print("  4: Full ECU Write (0x040000 - 0x200000, 1.75 MB, ~9 min)")
        print("  5: Get ECU Information (VIN, Software version, Config limits)")
        choice = input("Enter choice (1, 2, 3, 4, or 5): ").strip()
        
    is_write = (choice == '3' or choice == '4')
    
    if choice == '1':
        read_start = 0x1C2000
        read_end = 0x200000
        output_filename = "ME961_Calibration_Backup.bin"
        description = "Engine Calibration Read"
    elif choice == '2':
        read_start = 0x000000
        read_end = 0x200000
        output_filename = "ME961_Full_ECU_Backup.bin"
        description = "Full ECU Read"
    elif choice == '3':
        read_start = 0x1C2000
        read_end = 0x200000
        input_filename = "ME961_Calibration_Backup.bin"
        description = "Engine Calibration Write"
    elif choice == '4':
        read_start = 0x040000
        read_end = 0x200000
        input_filename = "ME961_Full_ECU_Backup.bin"
        description = "Full ECU Write"
    elif choice == '5':
        description = "Get ECU Information"
    else:
        print("[FAIL] Invalid choice.")
        return

    print(f"\nStarting {description}...")
    app_logger.info(f"=== Starting {description} ===")

    # For write, verify input file presence and size first
    file_data = None
    if is_write:
        cwd = os.getcwd()
        input_path = os.path.join(cwd, input_filename)
        if not os.path.exists(input_path):
            print(f"[FAIL] Backup file '{input_path}' not found. Please read first.")
            app_logger.error(f"Input file {input_path} not found.")
            return
        
        file_size = os.path.getsize(input_path)
        # Accept 2MB full layout or exact 248KB chunk for Option 3
        if choice == '3':
            if file_size != 0x200000 and file_size != (0x200000 - 0x1C2000):
                print(f"[FAIL] Invalid calibration file size ({file_size} bytes). Must be 2,097,152 bytes or 253,952 bytes.")
                app_logger.error(f"Invalid file size: {file_size}")
                return
        elif choice == '4':
            if file_size != 0x200000:
                print(f"[FAIL] Invalid full ECU backup file size ({file_size} bytes). Must be 2,097,152 bytes.")
                app_logger.error(f"Invalid file size: {file_size}")
                return
            
        with open(input_path, "rb") as f:
            raw_bytes = f.read()
            if choice == '3':
                if len(raw_bytes) == 0x200000:
                    file_data = raw_bytes[0x1C2000:0x200000]
                else:
                    file_data = raw_bytes
            elif choice == '4':
                file_data = raw_bytes[0x040000:0x200000]

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

        if choice == '5':
            print("\nReading ECU Information via GMLAN (ReadDataByIdentifier)...")
            vin = gmlan.get_vehicle_vin()
            serial = gmlan.get_serial_number()
            hw_type = gmlan.get_hardware_type()
            supplier = gmlan.get_supplier_id()
            diag_addr = gmlan.get_diagnostic_address()
            build_date = gmlan.get_build_date()
            prog_date = gmlan.get_programming_date_me96()
            
            main_os = gmlan.get_main_os()
            eng_cal = gmlan.get_engine_calib()
            sys_cal = gmlan.get_system_calib()
            spd_cal = gmlan.get_speedo_calib()
            slv_os = gmlan.get_slave_os()
            
            top_speed = gmlan.get_top_speed()
            radum = gmlan.get_radum()
            pmc_w = gmlan.get_pmc_w()
            saab_pn = gmlan.get_saab_partnumber()
            end_pn = gmlan.get_end_model_partnumber()
            base_pn = gmlan.get_base_model_partnumber()
            
            print("\n=================== ECU INFO ===================")
            print(f"  VIN:                       {vin}")
            print(f"  Serial Number:             {serial}")
            print(f"  Diagnostic Address:        {diag_addr}")
            print(f"  Hardware Type:             {hw_type}")
            print(f"  Supplier ID:               {supplier}")
            print(f"  Build Date:                {build_date}")
            print(f"  Programming Date:          {prog_date}")
            print(f"  Saab Part Number:          {saab_pn}")
            print(f"  End Model Part Number:     {end_pn}")
            print(f"  Base Model Part Number:    {base_pn}")
            print("----------------- Software Versions -------------")
            print(f"  Main OS:                   {main_os}")
            print(f"  Engine Calib:              {eng_cal}")
            print(f"  System Calib:              {sys_cal}")
            print(f"  Speedo Calib:              {spd_cal}")
            print(f"  Slave OS:                  {slv_os}")
            print("----------------- Config / Limits ---------------")
            print(f"  Speed Limiter:             {top_speed}")
            print(f"  Radum (Wheel Size):        {radum}")
            print(f"  Pmc W (Bus Config):        {pmc_w}")
            print("=================================================")
            return

        print("\n[1/3] Setting Up Programming Session...")
        app_logger.info("Setting up programming session...")
        
        # 1. Entering Programming Session
        if not gmlan.enter_programming_mode():
            print("  [FAIL] ECU denied programming session (0x10 0x02).")
            app_logger.error("ECU denied programming session.")
            return
        print("  [OK] Programming Session Active.")
        
        if is_write:
            # 2. Disable Normal Communications (Shutup)
            print("  Disabling normal CAN communication (0x28)...")
            if not gmlan.disable_normal_communication():
                print("  [FAIL] Could not disable normal CAN communication.")
                return
                
            # 3. Report Programmed State
            print("  Verifying ECU programmed state (0xA2)...")
            if not gmlan.report_programmed_state():
                print("  [FAIL] Report Programmed State failed.")
                return
                
            # 4. Request Programming Mode (A5 01)
            print("  Requesting programming mode (0xA5 0x01)...")
            if not gmlan.request_programming_mode_a501():
                print("  [FAIL] Programming mode request rejected.")
                return
                
            # 5. Enable Programming Mode (A5 03)
            print("  Enabling programming mode (0xA5 0x03)...")
            gmlan.enable_programming_mode_a503()
            time.sleep(0.05)
            gmlan.send_tester_present()

        print("\n[2/3] Performing Security Authentication...")
        app_logger.info("Performing security authentication (Security Access)...")
        if not gmlan.authenticate():
            print("  [FAIL] Security Access rejected.")
            app_logger.error("Security Access denied.")
            return
        app_logger.info("Security Access granted.")
        print("  [OK] Security Unlocked.")

        if is_write:
            print("\n[3/3] Initiating FLASH Download Session...")
            app_logger.info("Initiating FLASH download session...")
            
            erase_size = (read_end - read_start) if choice == '3' else 0x180000
            if choice == '3':
                erase_size = 0x02E000  # 188,416 bytes exact calibration download size
            if not gmlan.request_download(erase_size):
                print("  [FAIL] RequestDownload failed or timed out.")
                app_logger.error("RequestDownload failed.")
                return
            print("  [OK] Download Session Initialized.")
            
            print(f"\nWriting Blocks to ECU...")
            app_logger.info("Starting programming loop...")
            
            start_time = time.time()
            
            block_size = 4088
            current_addr = read_start
            block_seq = 0
            
            # Target length represents actual physical area to write (minus any skipped gaps)
            physical_write_length = (read_end - read_start)
            if choice == '4':
                physical_write_length -= (0x1C2000 - 0x1C0000)  # subtract 8 KB gap
                
            bytes_written = 0
            
            while current_addr < read_end:
                # Handle gaps (Option 4 skips the unreadable 0x1C0000 - 0x1C2000 range)
                if choice == '4' and current_addr == 0x1C0000:
                    app_logger.info("Skipping unreadable gap (0x1C0000 - 0x1C2000) in programming loop.")
                    current_addr = 0x1C2000
                    
                # Calculate remaining chunk length
                remaining = read_end - current_addr
                chunk_len = min(block_size, remaining)
                
                # Slice chunk from file_data using offset relative to read_start
                file_offset = current_addr - read_start
                chunk = file_data[file_offset : file_offset + chunk_len]
                
                if not gmlan.write_memory_block(current_addr, chunk, block_seq):
                    print(f"\n[FAIL] Flashing aborted at 0x{current_addr:06X}.")
                    app_logger.error(f"TransferData failed at 0x{current_addr:06X}")
                    return
                    
                block_seq = (block_seq + 1) & 0xFF
                    
                current_addr += chunk_len
                bytes_written += chunk_len
                
                progress = (bytes_written / physical_write_length) * 100
                elapsed = time.time() - start_time
                elapsed_m = int(elapsed // 60)
                elapsed_s = int(elapsed % 60)
                print(f"  [Progress] {progress:.1f}% written (Offset: 0x{current_addr:06X}) | Elapsed: {elapsed_m}m {elapsed_s}s", end='\r')
                
            elapsed = time.time() - start_time
            elapsed_m = int(elapsed // 60)
            elapsed_s = int(elapsed % 60)
            print(f"\n\n  [OK] SUCCESS! Flashing completed successfully.")
            print(f"  Total time elapsed: {elapsed_m}m {elapsed_s}s.")
            
            print("\nResetting ECU (0x20)...")
            gmlan.return_to_normal_mode()
            print("  [OK] ECU reset completed. Returning to normal mode.")
            app_logger.info("ECU successfully flashed and reset.")
            
        else:
            # ME9.6.1 Full Flash Layout Requirement: Exactly 2 MB (0x200000 bytes)
            total_flash_size = 0x200000  # 2,097,152 bytes
            full_flash_image = bytearray(b'\xFF' * total_flash_size)

            high_speed_chunk = 0xFA  # 250 bytes
            fallback_chunk = 0x02    # 2 bytes granular fallback if needed
            current_addr = read_start
            end_addr = read_end
            target_length = end_addr - read_start

            print(f"\n[3/3] Dumping memory region (0x{read_start:06X} - 0x{end_addr:06X})...")
            app_logger.info(f"Starting memory dump from 0x{read_start:06X} to 0x{end_addr:06X}")

            last_tp_time = time.time()
            start_time = time.time()

            while current_addr < end_addr:
                remaining = end_addr - current_addr
                fetch_size = min(high_speed_chunk, remaining)

                # Keep session alive by sending Tester Present (0x3E) every 2 seconds
                if time.time() - last_tp_time >= 2.0:
                    gmlan.send_tester_present()
                    last_tp_time = time.time()

                try:
                    # Attempt High-Speed Block Read (250 bytes / 0xFA)
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

                # Calculate and display progress relative to the read block
                bytes_read = current_addr - read_start
                progress = (bytes_read / target_length) * 100
                elapsed = time.time() - start_time
                elapsed_m = int(elapsed // 60)
                elapsed_s = int(elapsed % 60)
                print(f"  [Progress] {progress:.1f}% complete (Offset: 0x{current_addr:06X}) | Elapsed: {elapsed_m}m {elapsed_s}s", end='\r')

            # Save absolute path 2MB file
            cwd = os.getcwd()
            filename = os.path.join(cwd, output_filename)
            
            with open(filename, "wb") as f:
                f.write(full_flash_image)
                
            elapsed = time.time() - start_time
            elapsed_m = int(elapsed // 60)
            elapsed_s = int(elapsed % 60)
            print(f"\n\n  [OK] SUCCESS! Complete 2MB flash file with correct offsets saved to:\n  {filename} ({len(full_flash_image)} bytes).")
            print(f"  Total time elapsed: {elapsed_m}m {elapsed_s}s.")
            app_logger.info(f"Full 2MB flash file saved to: {filename} | Total time: {elapsed_m}m {elapsed_s}s")

    finally:
        adapter.disconnect()
        print("[Kvaser] Disconnected.")
        app_logger.info("Kvaser interface disconnected.")

if __name__ == "__main__":
    main()