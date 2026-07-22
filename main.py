import time
from adapters.kvaser import KvaserAdapter
from ecus import Motronic961
from gmlan import GMLANClient

def main():
    print("=== GMLAN Flasher Bench Test (Native Kvaser CANlib) ===")
    
    ecu = Motronic961()
    print(f"Target ECU : {ecu.NAME}")
    print(f"CAN IDs    : TX=0x{ecu.CAN_ID_TX:X}, RX=0x{ecu.CAN_ID_RX:X}\n")

    adapter = KvaserAdapter(channel=0)
    if not adapter.connect(baudrate=500000):
        return

    try:
        # Check physical bus status
        adapter.check_bus_status()

        gmlan = GMLANClient(adapter, ecu)

        print("\n[1/2] Requesting Diagnostic Session 0x02 (Programming)...")
        if gmlan.enter_programming_mode():
            print("  [SUCCESS] ECU responded!")
            
            print("\n[2/2] Initiating Security Access Handshake...")
            if gmlan.authenticate():
                print("\n🎉 Bench test passed! ME9.6.1 unlocked successfully.")
            else:
                print("\n[FAIL] Security Access rejected by ECU.")
        else:
            print("  [FAIL] ECU did not respond or rejected session request.")
            # Re-check bus status after failure to see if bus went BUS-OFF during transmit
            adapter.check_bus_status()

    finally:
        adapter.disconnect()

if __name__ == "__main__":
    main()
