"""
CAN Bus Trace Logger and .asc / CSV Exporter.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass(frozen=True)
class TraceFrame:
    timestamp: float
    channel: str
    can_id: int
    direction: str  # "Rx" or "Tx"
    data: bytes


class CANLogger:
    """Thread-safe recorder for raw CAN bus traffic and trace diagnostics."""

    def __init__(self):
        self._lock = threading.Lock()
        self._frames: List[TraceFrame] = []
        self._start_time = time.time()

    def log(self, can_id: int, data: bytes, direction: str = "Rx", channel: str = "CAN1") -> None:
        frame = TraceFrame(
            timestamp=time.time() - self._start_time,
            channel=channel,
            can_id=can_id,
            direction=direction,
            data=bytes(data),
        )
        with self._lock:
            self._frames.append(frame)

    def clear(self) -> None:
        with self._lock:
            self._frames.clear()
            self._start_time = time.time()

    def get_frames(self) -> List[TraceFrame]:
        with self._lock:
            return list(self._frames)

    def export_vector_asc(self, target_path: str) -> None:
        """Export trace to standard ASCII .asc log format."""
        path = Path(target_path)
        frames = self.get_frames()
        lines = [
            "date Wed Jan 01 00:00:00.000 2026",
            "base hex timestamps absolute",
            "internal events logged",
            "// PythonFlasher Native ASC Trace",
        ]
        for f in frames:
            dlc = len(f.data)
            payload_str = " ".join(f"{b:02X}" for b in f.data)
            dir_str = "Rx" if f.direction.lower().startswith("r") else "Tx"
            lines.append(f"{f.timestamp:10.6f} {f.channel} {f.can_id:08X} {dir_str} d {dlc} {payload_str}")

        path.write_text("\n".join(lines), encoding="utf-8")

    def export_csv(self, target_path: str) -> None:
        """Export trace to CSV format."""
        path = Path(target_path)
        frames = self.get_frames()
        lines = ["Timestamp,Channel,CanID,Direction,DLC,DataHex"]
        for f in frames:
            lines.append(
                f"{f.timestamp:.6f},{f.channel},0x{f.can_id:03X},{f.direction},{len(f.data)},{f.data.hex().upper()}"
            )
        path.write_text("\n".join(lines), encoding="utf-8")
