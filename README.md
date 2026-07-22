# PythonFlasher ⚡

> **Modular GMLAN / UDS ECU Diagnostic & Flashing Tool**

PythonFlasher is a modern, high-performance Python application and GUI designed for reading, writing, and diagnosing Engine Control Units (ECUs) used in **Saab, Opel/Vauxhall, GM, and Alfa Romeo** vehicles over CANbus (GMLAN / ISO 14229 / ISO 15765 / KWP2000).

---

## 📌 Background

In the automotive tuning and repair community, reading and writing ECU firmware often requires expensive proprietary hardware interfaces or legacy OEM software toolchains. 

**PythonFlasher** was built to provide a clean, modular, and open-source platform that:
- Runs natively on modern Python environments (Python 3.10+).
- Provides a clean architecture separating **Hardware Adapters**, **ISO-TP Transport Layers**, and **ECU Modules**.
- Offers both an interactive **PyQt5 Desktop GUI** and a lightweight **Command Line Interface (CLI)**.
- Features real-time CAN trace logging, automatic fallbacks, and OEM seed/key security algorithms.

---

## 🚦 Current Status

### ECU Support Matrix

| ECU Module | Target Vehicle / Engine | Status | Read | Write | Security Access |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Bosch ME(D)9.6.1** | Saab 9-3 2.8T V6 / Opel Vectra C V6 | ✅ **Tested & Working** | ✅ Full & Calib | ✅ Calibration | ✅ Level 1 (16-bit) |
| **Bosch EDC16C39** | Saab 9-3 1.9 TiD/TTiD, Opel 1.9/2.0 CDTI | 🚧 **In Development** | 🚧 Full & Calib | 🚧 Calibration | 🚧 Level 1 & Level 7 |
| **Bosch ME9.6** | Saab 9-3 / Opel 2.8T | 📋 **In Planning** | 📋 Planned | 📋 Planned | 📋 Planned |
| **Trionic 8 (T8)** | Saab 9-3 2.0t / 2.0T B207 | 📋 **In Planning** | 📋 Planned | 📋 Planned | 📋 Planned |
| **Bosch EDC17C19** | Opel / Vauxhall 2.0 CDTI | 📋 **In Planning** | 📋 Planned | 📋 Planned | 📋 Planned |

### Hardware Adapter Status

| Interface Adapter | Implementation | Status |
| :--- | :--- | :---: |
| **Kvaser** | Official Kvaser `canlib` SDK | ✅ **Tested & Working** |
| **J2534 PassThru** | Tactrix OpenPort, Scanmatik, Mongoose, etc. | 🚧 **In Development** |
| **STN Interfaces** | STN11xx / STN22xx / OBDLink | 📋 **In Planning** |

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

*This software is intended for educational, diagnostic, and research purposes only. Flashing engine control units carries inherent risks of bricking the ECU if interrupted or misused. Always maintain a full backup of your original ECU software and ensure a stable 12V+ power supply during read/write operations.*

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
