"""
SAE J2012 Diagnostic Trouble Code (DTC) Database and Freeze-Frame Inspector.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class DtcInfo:
    code_raw: int
    code_formatted: str
    description: str
    status_byte: int
    is_active: bool
    is_pending: bool
    status_flags: Tuple[str, ...] = ()
    freeze_frame: Optional[Dict[str, str]] = None


KNOWN_DTCS: Dict[str, str] = {
    "P0601": "Internal Control Module Memory Check Sum Error",
    "P0602": "Control Module Programming Error",
    "P0606": "ECU Processor / Internal Performance Defect",
    "P0300": "Random or Multiple Cylinder Misfire Detected",
    "P0100": "Mass or Volume Air Flow Circuit Malfunction",
    "P0101": "Mass or Volume Air Flow Circuit Range/Performance Problem",
    "P0102": "Mass or Volume Air Flow Circuit Low Input",
    "P0103": "Mass or Volume Air Flow Circuit High Input",
    "P0115": "Engine Coolant Temperature Circuit Malfunction",
    "P0120": "Throttle/Pedal Position Sensor/Switch A Circuit Malfunction",
    "P0335": "Crankshaft Position Sensor A Circuit Malfunction",
    "P0340": "Camshaft Position Sensor A Circuit Malfunction",
    "P0420": "Catalyst System Efficiency Below Threshold (Bank 1)",
    "P0500": "Vehicle Speed Sensor A Malfunction",
    "P1230": "Throttle Position Sensor 1 and 2 Circuit: Sum Out of Range",
    "P1231": "Throttle Position Sensor 1 and 2 Circuit: Sum Out of Range (No Limp Home)",
    "P1460": "Immobilizer Active",
    "P1530": "Pedal Position Sensor 1 and 2 Circuit: Sum Out of Range",
    "P1600": "Loss of Engine Serial Data / ECU Internal Security Denial",
    "P1626": "Theft Deterrent Fuel Enable Signal Not Received",
    "U0001": "High Speed CAN Communication Bus Error",
    "U0100": "Lost Communication With ECM/PCM 'A'",
    "U0101": "Lost Communication With Transmission Control Module (TCM)",
    "U0121": "Lost Communication With Anti-Lock Brake System (ABS) Module",
    "U2105": "GMLAN CAN Bus Communication Failure with ECM",
}

# DTC status byte bit meanings, bit 0 (0x01) through bit 7 (0x80). This is
# the standard ISO 14229 (UDS) layout, which GMLAN (T8) and T7's KWP-based
# protocol both follow closely enough for this to apply. It does not really
# apply to T5: T5 predates this convention and doesn't expose DTCs as
# (code, status byte) pairs at all — its fault data is a set of named RAM
# error counters instead (see the T5-specific handling this module doesn't
# have, since T5 was never wired into lookup_dtc()'s (high_byte, low_byte)
# calling convention to begin with).
_STATUS_BIT_MEANINGS: Tuple[Tuple[int, str], ...] = (
    (0x01, "test failed at the time of the request"),
    (0x02, "test failed on the current operation cycle"),
    (0x04, "pending: failed on the current or previous operation cycle"),
    (0x08, "confirmed at the time of the request"),
    (0x10, "test not completed since the last code clear"),
    (0x20, "test failed at least once since last code clear"),
    (0x40, "test not completed this operation cycle"),
    (0x80, "warning indicator (MIL) requested"),
)


def decode_dtc_status_byte(status_byte: int) -> Tuple[str, ...]:
    """Expand a UDS DTC status byte into its individual set bit meanings."""
    return tuple(text for bit, text in _STATUS_BIT_MEANINGS if status_byte & bit)


def format_dtc_code(high_byte: int, low_byte: int) -> str:
    """Format 2-byte DTC value into standard SAE J2012 string (e.g. P0601)."""
    category_bits = (high_byte >> 6) & 0x03
    prefix = {0: "P", 1: "C", 2: "B", 3: "U"}[category_bits]
    digit1 = (high_byte >> 4) & 0x03
    digit2 = high_byte & 0x0F
    digit3 = (low_byte >> 4) & 0x0F
    digit4 = low_byte & 0x0F
    return f"{prefix}{digit1:X}{digit2:X}{digit3:X}{digit4:X}"


def lookup_dtc(high_byte: int, low_byte: int, status_byte: int = 0x2F) -> DtcInfo:
    """Lookup DTC description and parse status flags."""
    formatted = format_dtc_code(high_byte, low_byte)
    description = KNOWN_DTCS.get(formatted, "Manufacturer Specific Diagnostic Fault Code")
    raw_code = (high_byte << 8) | low_byte
    is_active = bool(status_byte & 0x09)
    is_pending = bool(status_byte & 0x04)

    return DtcInfo(
        code_raw=raw_code,
        code_formatted=formatted,
        description=description,
        status_byte=status_byte,
        is_active=is_active,
        is_pending=is_pending,
        status_flags=decode_dtc_status_byte(status_byte),
    )


def parse_freeze_frame(data: bytes) -> Dict[str, str]:
    """Parse diagnostic freeze-frame PID snapshot data."""
    if len(data) < 4:
        return {"Status": "Raw payload too short for freeze-frame breakdown"}

    rpm = int.from_bytes(data[0:2], "big") / 4.0 if len(data) >= 2 else 0.0
    temp_c = data[2] - 40 if len(data) >= 3 else 0
    speed_kmh = data[3] if len(data) >= 4 else 0

    return {
        "Engine Speed": f"{rpm:.0f} RPM",
        "Coolant Temp": f"{temp_c} °C",
        "Vehicle Speed": f"{speed_kmh} km/h",
    }
