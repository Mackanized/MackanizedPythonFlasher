"""Deterministic, strict CAN trace replay adapter."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from adapters.base_adapter import BaseAdapter


class TraceFormatError(ValueError):
    """A trace fixture is malformed or unsuitable for replay."""


class TraceMismatchError(AssertionError):
    """The client transmitted a frame different from the replay contract."""


@dataclass(frozen=True)
class TraceFrame:
    direction: str
    can_id: int
    data: bytes
    note: str = ""


@dataclass(frozen=True)
class ReplayTrace:
    name: str
    ecu: str
    evidence: str
    source_reference: str
    frames: Tuple[TraceFrame, ...]

    @classmethod
    def from_path(cls, path: Path) -> "ReplayTrace":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TraceFormatError(f"Unable to load trace {path}: {exc}") from exc
        if payload.get("schema_version") != 1:
            raise TraceFormatError("Unsupported replay trace schema")
        evidence = str(payload.get("evidence", ""))
        if evidence not in {"captured", "synthetic-reference", "synthetic-test"}:
            raise TraceFormatError("Replay trace must state captured or synthetic evidence")
        frames = []
        for index, item in enumerate(payload.get("frames", ())):
            direction = str(item.get("direction", "")).lower()
            if direction not in {"tx", "rx"}:
                raise TraceFormatError(f"Trace frame {index} has invalid direction")
            try:
                can_id = int(str(item["can_id"]), 0)
                data = bytes.fromhex(str(item["data"]))
            except (KeyError, ValueError) as exc:
                raise TraceFormatError(f"Trace frame {index} has invalid CAN data") from exc
            if not 0 <= can_id <= 0x1FFFFFFF or not 1 <= len(data) <= 8:
                raise TraceFormatError(f"Trace frame {index} exceeds classic CAN bounds")
            frames.append(TraceFrame(direction, can_id, data, str(item.get("note", ""))))
        if not frames:
            raise TraceFormatError("Replay trace contains no frames")
        return cls(
            name=str(payload.get("name", path.stem)),
            ecu=str(payload.get("ecu", "unknown")),
            evidence=evidence,
            source_reference=str(payload.get("source_reference", "")),
            frames=tuple(frames),
        )


@dataclass(frozen=True)
class ReplayStatistics:
    tx_frames: int
    rx_frames: int
    tx_bytes: int
    rx_bytes: int
    sampled_at: float
    nominal_bitrate: int


class ReplayAdapter(BaseAdapter):
    """Adapter that consumes expected TX frames and returns recorded RX frames."""

    def __init__(self, trace: ReplayTrace) -> None:
        super().__init__()
        self.trace = trace
        self._connected = False
        self._cursor = 0

    @property
    def is_simulation(self) -> bool:
        return True

    @property
    def is_replay(self) -> bool:
        return True

    def is_connected(self) -> bool:
        return self._connected

    @property
    def remaining_frames(self) -> int:
        return len(self.trace.frames) - self._cursor

    def statistics(self) -> ReplayStatistics:
        return ReplayStatistics(
            tx_frames=sum(1 for frame in self.trace.frames[:self._cursor] if frame.direction == "tx"),
            rx_frames=sum(1 for frame in self.trace.frames[:self._cursor] if frame.direction == "rx"),
            tx_bytes=self._tx_bytes,
            rx_bytes=self._rx_bytes,
            sampled_at=time.monotonic(),
            nominal_bitrate=self._nominal_bitrate,
        )

    def connect(self, baudrate: int = 500000) -> bool:
        self._set_nominal_bitrate(baudrate)
        self._cursor = 0
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def send_frame(self, can_id: int, data: bytes) -> bool:
        self._require_connected()
        self._assert_channel_access()
        expected = self._next("tx")
        actual_data = bytes(data)
        if can_id != expected.can_id or actual_data != expected.data:
            raise TraceMismatchError(
                f"{self.trace.name} frame {self._cursor - 1}: expected TX "
                f"0x{expected.can_id:X} {expected.data.hex(' ')}, got "
                f"0x{can_id:X} {actual_data.hex(' ')}"
            )
        self._record_tx(len(actual_data))
        return True

    def read_frame(self, timeout_ms: int = 1000) -> Tuple[int, bytes]:
        del timeout_ms
        self._require_connected()
        self._assert_channel_access()
        if self._cursor >= len(self.trace.frames):
            return 0, b""
        if self.trace.frames[self._cursor].direction != "rx":
            return 0, b""
        frame = self._next("rx")
        self._record_rx(len(frame.data))
        return frame.can_id, frame.data

    def assert_complete(self) -> None:
        if self.remaining_frames:
            frame = self.trace.frames[self._cursor]
            raise TraceMismatchError(
                f"{self.trace.name} replay incomplete: {self.remaining_frames} frame(s) remain; "
                f"next is {frame.direction.upper()} 0x{frame.can_id:X}"
            )

    def _next(self, direction: str) -> TraceFrame:
        if self._cursor >= len(self.trace.frames):
            raise TraceMismatchError(f"{self.trace.name} has no remaining {direction.upper()} frame")
        frame = self.trace.frames[self._cursor]
        if frame.direction != direction:
            raise TraceMismatchError(
                f"{self.trace.name} frame {self._cursor}: expected a {frame.direction.upper()} "
                f"operation, client attempted {direction.upper()}"
            )
        self._cursor += 1
        return frame

    def _require_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("Replay adapter is not connected")
