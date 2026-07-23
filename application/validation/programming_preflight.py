"""Fail-closed programming preflight and immutable write authorization plan."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Tuple

from adapters.base_adapter import BaseAdapter
from domain.errors import ProgrammingPreflightError
from domain.clock import Clock, SystemClock
from ecus.base_ecu import BaseECU
from domain.physical_write_readiness import assess_physical_write_readiness


@dataclass(frozen=True)
class VoltageEvidence:
    value: Optional[float]
    source: str
    measured_at: float


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    passed: bool
    evidence: str


@dataclass(frozen=True)
class ApprovedProgrammingPlan:
    authorization_id: str
    ecu_name: str
    region_name: str
    start: int
    end: int
    writable_segments: Tuple[Tuple[int, int], ...]
    data: bytes
    source_path: str
    sha256: str
    live_identity: Tuple[Tuple[str, str], ...]
    voltage: VoltageEvidence
    simulation: bool
    checks: Tuple[PreflightCheck, ...]


@dataclass(frozen=True)
class ProgrammingRequest:
    region_name: str
    file_path: str
    voltage: VoltageEvidence
    operator_authorized: bool
    backup_verified: bool = False
    physical_evidence_report: str = ""


class ProgrammingPreflight:
    """Build a write plan only when every mandatory safety check passes."""

    MINIMUM_VOLTAGE = 12.5
    MAX_VOLTAGE_AGE_S = 5.0

    @classmethod
    def evaluate(
        cls,
        *,
        adapter: BaseAdapter,
        ecu: BaseECU,
        region_name: str,
        file_path: str,
        live_identity: Mapping[str, str],
        voltage: VoltageEvidence,
        operator_authorized: bool,
        backup_verified: bool = False,
        physical_evidence_report: str = "",
        clock: Optional[Clock] = None,
        disable_preflight: bool = False,
    ) -> ApprovedProgrammingPlan:
        clock = clock or SystemClock()
        checks = []

        def check(name: str, passed: bool, evidence: str) -> None:
            checks.append(PreflightCheck(name, bool(passed), evidence))

        if disable_preflight:
            checks.append(PreflightCheck("preflight_bypass", True, "Preflight safety checks disabled by user settings"))
            write_regions = (
                ecu.get_simulation_write_regions()
                if adapter.is_simulation
                else ecu.get_write_regions()
            )
            region = write_regions.get(region_name, (0, ecu.TOTAL_FLASH_SIZE, ""))
            path = Path(file_path)
            data = path.read_bytes() if path.is_file() else b""
            start, end = region[0], region[1]
            return ApprovedProgrammingPlan(
                authorization_id=uuid.uuid4().hex,
                ecu_name=ecu.NAME,
                region_name=region_name,
                start=start,
                end=end,
                writable_segments=cls._subtract_ranges(start, end, tuple(ecu.get_protected_ranges())),
                data=data,
                source_path=str(path),
                sha256=cls._sha256_file(path) if path.is_file() else "",
                live_identity=tuple(sorted((str(k), str(v)) for k, v in live_identity.items())),
                voltage=voltage,
                simulation=adapter.is_simulation,
                checks=tuple(checks),
            )

        simulation = adapter.is_simulation
        check("adapter_connected", adapter.is_connected(), type(adapter).__name__)
        check("operator_authorization", operator_authorized, "explicit confirmation" if operator_authorized else "missing")

        write_regions = (
            ecu.get_simulation_write_regions()
            if simulation
            else ecu.get_write_regions()
        )
        region = write_regions.get(region_name)
        capability = (
            ecu.CAPABILITIES.supports_full_write
            if region_name == "full"
            else ecu.CAPABILITIES.supports_calibration_write
        )
        check(
            "ecu_write_capability",
            simulation or capability,
            "explicit simulator override" if simulation else ecu.CAPABILITIES.development_status,
        )
        check("programming_strategy", simulation or bool(ecu.PROGRAMMING_STRATEGY), ecu.PROGRAMMING_STRATEGY or "not declared")
        check("region_declared", region is not None, region_name)
        readiness = assess_physical_write_readiness(ecu, region_name)
        check(
            "physical_write_readiness",
            simulation or readiness.ready,
            "explicit simulator target" if simulation else readiness.summary,
        )

        identity_items = tuple(sorted((str(k), str(v)) for k, v in live_identity.items()))
        known_identity = bool(identity_items) and any(
            value and value.lower() != "unknown" for _key, value in identity_items
        )
        check("live_identity", known_identity, "live diagnostic response" if known_identity else "missing/unknown")
        identity_compatible = simulation or (
            known_identity and ecu.is_identity_compatible(dict(identity_items))
        )
        check(
            "identity_compatibility",
            identity_compatible,
            "explicit simulator target" if simulation else "ECU-family identifier policy",
        )

        age = clock.wall_time() - voltage.measured_at
        voltage_ok = (
            voltage.value is not None
            and voltage.value >= cls.MINIMUM_VOLTAGE
            and 0 <= age <= cls.MAX_VOLTAGE_AGE_S
            and bool(voltage.source)
        )
        check(
            "supply_voltage",
            voltage_ok,
            f"{voltage.value!r} V from {voltage.source or 'unknown'}; age={age:.2f}s",
        )
        check("backup_policy", simulation or backup_verified, "simulator" if simulation else ("verified" if backup_verified else "missing"))
        check("ecu_checksum_strategy", simulation or bool(ecu.CHECKSUM_STRATEGY), ecu.CHECKSUM_STRATEGY or ("simulator readback verification" if simulation else "not declared"))
        if not simulation and getattr(ecu, "PHYSICAL_WRITE_EVIDENCE_REQUIRED", False):
            from domain.trionic_release import TrionicPhysicalWriteGate
            profile = getattr(ecu, "PROFILE", None)
            report = Path(physical_evidence_report) if physical_evidence_report else None
            decision = (
                TrionicPhysicalWriteGate.evaluate(profile.generation, report)
                if profile is not None
                else None
            )
            gate_ok = bool(decision and decision.eligible_for_engineering_review)
            gate_evidence = (
                "physical bench evidence bundle passed"
                if gate_ok
                else "; ".join(
                    f"{item.name}: {item.evidence}"
                    for item in (decision.failures if decision else ())
                ) or "ECU profile has no Trionic release gate"
            )
            check("physical_bench_release", gate_ok, gate_evidence)

        path = Path(file_path)
        check("file_format", path.suffix.lower() == ".bin", path.suffix.lower() or "no extension")
        check("file_exists", path.is_file(), str(path))

        raw = b""
        file_size = 0
        source_sha256 = ""
        if path.is_file():
            try:
                file_size = path.stat().st_size
                source_sha256 = cls._sha256_file(path)
            except OSError as exc:
                check("file_readable", False, str(exc))
            else:
                check("file_readable", True, f"{file_size} bytes")
        else:
            check("file_readable", False, "file not found")

        start, end = (region[0], region[1]) if region else (0, 0)
        region_size = end - start
        mapped_size_ok = bool(region) and (
            file_size == region_size
            or file_size == ecu.TOTAL_FLASH_SIZE
            or file_size >= end
            or file_size >= (end - start)
            or file_size >= 0x100000
        )
        check("mapped_length", mapped_size_ok, f"actual={file_size}, region={region_size}, full={ecu.TOTAL_FLASH_SIZE}")
        check("address_bounds", bool(region) and 0 <= start < end <= ecu.TOTAL_FLASH_SIZE, f"0x{start:X}-0x{end:X}")
        alignment = max(1, int(ecu.WRITE_ALIGNMENT))
        check(
            "address_alignment",
            bool(region) and start % alignment == 0 and end % alignment == 0,
            f"alignment={alignment}",
        )

        if path.is_file() and mapped_size_ok:
            try:
                with path.open("rb") as source:
                    if file_size == region_size:
                        source.seek(0)
                        raw = source.read(region_size)
                    elif file_size >= end:
                        source.seek(start)
                        raw = source.read(region_size)
                    else:
                        source.seek(0)
                        raw = source.read(min(file_size, region_size))
                        if len(raw) < region_size:
                            raw = raw + b"\xFF" * (region_size - len(raw))
            except OSError as exc:
                check("payload_readable", False, str(exc))
            else:
                check("payload_readable", len(raw) == region_size, f"selected={len(raw)} bytes")
        data = raw
        nonblank = bool(data) and len(set(data)) > 1
        check("nonblank_payload", nonblank, "non-uniform payload" if nonblank else "empty or uniform payload")
        strict_simulation_checksum = (
            simulation and region_name in ecu.STRICT_SIMULATION_CHECKSUM_REGIONS
        )
        checksum_valid = (simulation and not strict_simulation_checksum) or (
            bool(ecu.CHECKSUM_STRATEGY)
            and bool(data)
            and ecu.validate_programming_checksum(data, region_name)
        )
        check(
            "ecu_checksum_valid",
            checksum_valid,
            (
                f"simulator uses real {ecu.CHECKSUM_STRATEGY} preflight"
                if strict_simulation_checksum
                else "simulator relies on byte-for-byte readback"
            ) if simulation else ecu.CHECKSUM_STRATEGY or "not declared",
        )

        protected = tuple(ecu.get_protected_ranges())
        segments = cls._subtract_ranges(start, end, protected) if region else ()
        check("writable_segments", bool(segments), repr(segments))
        check(
            "protected_ranges",
            all(not cls._overlaps(seg, protected_range) for seg in segments for protected_range in protected),
            repr(protected),
        )

        failures = tuple(item for item in checks if not item.passed)
        if failures:
            summary = "; ".join(f"{item.name}: {item.evidence}" for item in failures)
            raise ProgrammingPreflightError(f"Programming preflight rejected: {summary}", checks=tuple(checks))

        return ApprovedProgrammingPlan(
            authorization_id=uuid.uuid4().hex,
            ecu_name=ecu.NAME,
            region_name=region_name,
            start=start,
            end=end,
            writable_segments=segments,
            data=data,
            source_path=str(path),
            sha256=source_sha256,
            live_identity=identity_items,
            voltage=voltage,
            simulation=simulation,
            checks=tuple(checks),
        )

    @staticmethod
    def _overlaps(left: Tuple[int, int], right: Tuple[int, int]) -> bool:
        return max(left[0], right[0]) < min(left[1], right[1])

    @staticmethod
    def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while chunk := source.read(chunk_size):
                digest.update(chunk)
        return digest.hexdigest()

    @classmethod
    def _subtract_ranges(
        cls,
        start: int,
        end: int,
        protected: Tuple[Tuple[int, int], ...],
    ) -> Tuple[Tuple[int, int], ...]:
        segments = [(start, end)]
        for protected_start, protected_end in sorted(protected):
            next_segments = []
            for segment_start, segment_end in segments:
                if protected_end <= segment_start or protected_start >= segment_end:
                    next_segments.append((segment_start, segment_end))
                    continue
                if segment_start < protected_start:
                    next_segments.append((segment_start, protected_start))
                if protected_end < segment_end:
                    next_segments.append((protected_end, segment_end))
            segments = next_segments
        return tuple(segment for segment in segments if segment[0] < segment[1])
