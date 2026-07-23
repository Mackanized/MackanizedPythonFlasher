# PythonFlasher ⚡

> **Modular GMLAN / UDS ECU Diagnostic & Flashing Tool**

PythonFlasher is a modern, high-performance Python application and GUI designed for reading, writing, and diagnosing Engine Control Units (ECUs) used in **Saab, Opel/Vauxhall, GM, Alfa Romeo, and Holden** vehicles over CANbus (GMLAN / ISO 14229 / ISO 15765 / KWP2000).

---

## 👨‍💻 Author & Attribution

Developed by **Markus Södergren** (**Mackanized**) at **CMS DriveTech AB** in Sweden.

- **Community**: Active member on [TrionicTuning](http://www.trionictuning.com) and [Facebook](https://www.facebook.com/mackanized)
- **Website & Contact**: [www.mackanized.eu](http://www.mackanized.eu) or via [Facebook](https://www.facebook.com/mackanized)

---

## ☕ Support & Donations (Donationware)

PythonFlasher is free and open-source **Donationware**. If this project helps you tune, repair, or read your vehicle's ECU, contributions are greatly appreciated!

- **PayPal**: `paypal@drivetech.se`

---

## 📌 Background & Architecture

In the automotive tuning and repair community, reading and writing ECU firmware often requires expensive proprietary hardware interfaces or legacy OEM software toolchains.

**PythonFlasher** was built around **strict modularity**:

- **Plug-and-Play ECU Modules**: New ECUs are implemented as standalone `.py` classes inheriting from `BaseECU`. Adding support for a new ECU simply requires dropping a new file into `ecus/`!
- **Modular Hardware Adapters**: Universal interface layer for **Kvaser**, **J2534 PassThru**, and **STN**.
- **Transport & Flashing Engine**: Core ISO-TP engine and session state manager decoupled from user interfaces.
- **Dual UI Support**: Sleek **PyQt5 Desktop GUI** (`gui_main.py`) + **CLI Tool** (`flasher_cli.py`).

---

## 🧩 Adding a New ECU Module (Modularity Guide)

PythonFlasher makes it easy for developers and tuners to add support for new ECUs. Every ECU module lives in `ecus/` and inherits from `BaseECU`.

### **1. ECU Data & Property Requirements**

To dock a new ECU module, create a new `.py` file in `ecus/` (e.g. `ecus/my_new_ecu.py`) and define the following properties and methods:

```python
from typing import Dict, List, Tuple
from .base_ecu import BaseECU, Step

class MyNewECU(BaseECU):
    # ── 1. Metadata & Identifiers ────────────────────────────────────
    NAME = "Bosch MyNewECU"          # Display name in GUI/CLI
    CAN_ID_TX = 0x7E0                # Tester Request CAN ID
    CAN_ID_RX = 0x7E8                # ECU Response CAN ID
    SECURITY_LEVEL = 0x01            # SecurityAccess sub-function (0x01 = Level 1)
    ADDR_LEN_IDENTIFIER = 0x00       # Service $23 format byte (0x00 or 0x23)

    # ── 2. Seed-Key Transformation Steps ─────────────────────────────
    # List of 3-byte transformation steps (op_byte, param0, param1)
    SEED_KEY_STEPS = [
        Step(0xF8, 0x1F, 0x80),
        Step(0x05, 0x31, 0x6B),
        Step(0x2A, 0x03, 0x4D),
        Step(0x75, 0x68, 0x15),
    ]

    # ── 3. Flash Memory Layout & Block Sizes ─────────────────────────
    TOTAL_FLASH_SIZE = 0x200000      # 2 MB total flash footprint
    READ_HIGH_SPEED_CHUNK = 0xFA     # High-speed block size (250 bytes)
    READ_FALLBACK_CHUNK = 0x02       # Fallback chunk size (2 bytes)
    ERASE_SIZE = 0x180000            # Code erase block footprint
    WRITE_BLOCK_SIZE = 4088          # Write payload chunk size

    # Optional unreadable/reserved memory gaps to skip automatically:
    GAPS = [(0x1C0000, 0x1C2000)]

    # ── 4. Required Implementation Methods ───────────────────────────
    def get_flash_addresses(self) -> List[Tuple[int, int]]:
        """Returns list of (start_address, length) tuples for full memory read."""
        return [(0x000000, self.TOTAL_FLASH_SIZE)]

    def get_flash_regions(self) -> Dict[str, Tuple[int, int, str]]:
        """Named flash regions for reading: map name -> (start, end, default_filename)."""
        return {
            "calibration": (0x1C2000, 0x1F0000, "MyECU_Calibration.bin"),
            "full": (0x000000, self.TOTAL_FLASH_SIZE, "MyECU_Full_Backup.bin"),
        }

    def get_write_regions(self) -> Dict[str, Tuple[int, int, str]]:
        """Named flash regions for writing: map name -> (start, end, default_filename)."""
        return {
            "calibration": (0x1C2000, 0x1F0000, "MyECU_Calibration.bin"),
        }

    def get_info_pids(self) -> List[str]:
        """PID keys to query during ECU Identification (VIN, Serial, OS, Calib)."""
        return ["vin", "serial", "main_os", "calibration_set", "codefile_version"]

    def get_verify_pids(self) -> Dict[str, Tuple[int, str]]:
        """PIDs to verify calibration state after flash operations."""
        return {
            "engine_calib": (0xC2, "Engine Calibration"),
        }
```

### **2. Registering the Module**

1. Add the export to `ecus/__init__.py`:
   ```python
   from .my_new_ecu import MyNewECU
   ```
2. Add your ECU entry to the selection menu in `flasher_cli.py` and `gui/steps/step_ecu.py`.

---

## 🚦 Current Status

### ECU Support Matrix

| ECU Module            | GM Designation                                | Target Vehicles & Engines                                                                                                                                     |                  Status                   |      Read       |                  Write                   |   Security Access    |
| :-------------------- | :-------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------ | :---------------------------------------: | :-------------: | :--------------------------------------: | :------------------: |
| **Bosch ME(D)9.6.1**  | **GM E69** (MED9.6.1)<br>**GM E77** (ME9.6.1) | Saab 9-3 (2014), 9-4X (2011), 9-5 (2010–2011)<br>Opel/Vauxhall Insignia<br>GM North America & Holden Australia<br>_Engines: A20NHT, A28NER, A28NET, LP2, LAU_ |          ✅ **Tested & Working**          | ✅ Full & Calib |              ✅ Calibration              | ✅ Level 1 (16-bit)  |
| **Bosch EDC16C39**    | Bosch EDC16                                   | Saab 9-3 1.9 TiD/TTiD, Opel 1.9/2.0 CDTI                                                                                                                      |           🚧 **In Development**           | 🚧 Full & Calib |              🚧 Calibration              | 🚧 Level 1 & Level 7 |
| **Bosch ME9.6**       | GM E69                                        | Saab 9-3 / Opel 2.8T V6 (2006–2009)                                                                                                                           |            📋 **In Planning**             |   📋 Planned    |                📋 Planned                |      📋 Planned      |
| **Trionic 5.2 / 5.5** | Saab T5                                       | Saab 9000 / NG900 / early 9-3 B204/B234                                                                                                                       | 🧪 **Hardware-enabled, upstream-derived** |     ✅ Full     |                 ✅ Full                  |     SRAM loader      |
| **Trionic 7 (T7)**    | Saab T7                                       | Saab 9-3 / 9-5 B205/B235                                                                                                                                      | 🧪 **Hardware-enabled, upstream-derived** |     ✅ Full     |     ✅ Full, protected gap preserved     |   ✅ KWP 0x05/0x06   |
| **Trionic 8 (T8)**    | Saab T8                                       | Saab 9-3 2.0t / 2.0T (B207E/L/R)                                                                                                                              | 🧪 **Hardware-enabled, upstream-derived** |     ✅ Full     | ✅ Full image input, app partitions only |  ✅ GMLAN 0x01/0x02  |
| **Bosch EDC17C19**    | Bosch EDC17                                   | Opel / Vauxhall 2.0 CDTI                                                                                                                                      |            📋 **In Planning**             |   📋 Planned    |                📋 Planned                |      📋 Planned      |

The application still requires a connected adapter, live ECU identity, supported region, valid ECU checksum, fresh voltage evidence, explicit operator authorization, backup confirmation, protected-range handling, and post-write readback.

### Hardware Adapter Status

| Interface Adapter  | Implementation                              |         Status          |
| :----------------- | :------------------------------------------ | :---------------------: |
| **Kvaser**         | Official Kvaser `canlib` SDK                | ✅ **Tested & Working** |
| **J2534 PassThru** | Tactrix OpenPort, Scanmatik, Mongoose, etc. |  🚧 **In Development**  |
| **STN Interfaces** | STN11xx / STN22xx / OBDLink                 |   📋 **In Planning**    |

---

## 🛠️ Key Features

- **Dual User Interfaces**:
  - **PyQt5 GUI** (`gui_main.py`): Sleek dark theme wizard interface with real-time CAN trace monitor and progress metrics.
  - **CLI** (`flasher_cli.py`): Fast, menu-driven terminal tool for field use and headless operation.
- **OEM Diagnostic Read Capabilities**: Reads VIN, Hardware Type, Part Numbers, Software Versions, Diagnostic Data IDs, and BCD Programming Dates.
- **ISO-TP Transport Engine**: Robust multi-frame ISO-TP transmission with flow control handling and configurable block sizes.
- **Comprehensive Logging**:
  - `logs/flasher.log`: Structured application events and error logs.
  - `logs/cantrace.log`: High-resolution frame-by-frame CANbus transmit/receive trace.

---

## 🚀 Getting Started

### 1. Prerequisites & Virtual Environment

Clone the repository and set up a Python virtual environment:

```powershell
git clone https://github.com/MelvisR/PythonFlasher.git
cd PythonFlasher

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Launching the Application

#### **Command Line Interface (CLI)**

```powershell
.venv\Scripts\python flasher_cli.py
```

#### **PyQt5 Graphical Interface (GUI)**

```powershell
.venv\Scripts\python gui_main.py
```

---

## 🗺️ Future Roadmap

- [ ] Complete Bosch EDC16C39 in-car and bench flashing routines.
- [ ] Finalize J2534 PassThru driver implementation.
- [ ] Add STN interface support (STN11xx / STN22xx).
- [ ] Implement automated checksum verification prior to flash write operations.
- [ ] Cross-platform support (Linux SocketCAN driver).

---

## ⚠️ Disclaimer

_This software is intended for educational, diagnostic, and research purposes only. Flashing engine control units carries inherent risks of bricking the ECU if interrupted or misused. Always maintain a full backup of your original ECU software and ensure a stable 12V+ power supply during read/write operations._

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
