"""Physical-write release gate and physical bench evidence validation.

Passing this gate means an evidence bundle is internally consistent. It does
not automatically enable physical writes; that remains an explicit ECU-module
release decision after engineering review.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from domain.trionic import SOURCE_COMMIT, TrionicGeneration, get_trionic_profile
from firmware.trionic.loaders import LoaderCatalog, LoaderIntegrityError


_REQUIRED_SCENARIOS = {
    TrionicGeneration.T5_2: (
        "identify_before_write",
        "loader_upload_and_start",
        "interrupted_transfer_recovery",
        "post_recovery_readback",
        "post_reset_reconnect",
    ),
    TrionicGeneration.T5_5: (
        "identify_before_write",
        "loader_upload_and_start",
        "interrupted_transfer_recovery",
        "post_recovery_readback",
        "post_reset_reconnect",
    ),
    TrionicGeneration.T7: (
        "identify_before_write",
        "checksum_preflight",
        "protected_gap_preserved",
        "interrupted_transfer_recovery",
        "post_reset_reconnect",
    ),
    TrionicGeneration.T8: (
        "identify_before_write",
        "loader_upload_and_start",
        "recovery_address_entry",
        "interrupted_erase_recovery",
        "interrupted_transfer_recovery",
        "protected_partitions_preserved",
        "post_recovery_readback",
        "post_reset_reconnect",
    ),
}


@dataclass(frozen=True)
class ReleaseCheck:
    name: str
    passed: bool
    evidence: str


@dataclass(frozen=True)
class TrionicReleaseDecision:
    eligible_for_engineering_review: bool
    physical_write_enabled: bool
    generation: TrionicGeneration
    checks: Tuple[ReleaseCheck, ...]

    @property
    def failures(self) -> Tuple[ReleaseCheck, ...]:
        return tuple(check for check in self.checks if not check.passed)


class TrionicPhysicalWriteGate:
    """Validate software artifacts plus an operator-supplied bench bundle."""

    @classmethod
    def evaluate(
        cls,
        generation: TrionicGeneration,
        report_path: Optional[Path] = None,
        *,
        loader_catalog: Optional[LoaderCatalog] = None,
    ) -> TrionicReleaseDecision:
        checks = []

        def check(name: str, passed: bool, evidence: str) -> None:
            checks.append(ReleaseCheck(name, bool(passed), evidence))

        profile = get_trionic_profile(generation)
        catalog = loader_catalog or LoaderCatalog()
        try:
            artifacts = catalog.validate_all()
        except (LoaderIntegrityError, OSError) as exc:
            artifacts = ()
            check("loader_integrity", False, str(exc))
        else:
            check("loader_integrity", True, f"{len(artifacts)} pinned artifacts verified")

        check(
            "checksum_strategy",
            bool(profile.checksum_strategy),
            profile.checksum_strategy or "missing",
        )
        if report_path is None:
            check("physical_bench_report", False, "no physical bench evidence bundle supplied")
        else:
            cls._validate_report(
                generation,
                Path(report_path),
                {item.identifier: item.sha256 for item in artifacts},
                check,
            )

        eligible = bool(checks) and all(item.passed for item in checks)
        return TrionicReleaseDecision(
            eligible_for_engineering_review=eligible,
            # Deliberately never toggled by a data file. Enabling hardware
            # writes requires a reviewed code change after this gate passes.
            physical_write_enabled=False,
            generation=generation,
            checks=tuple(checks),
        )

    @classmethod
    def _validate_report(cls, generation, path, loader_hashes, check) -> None:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            check("physical_bench_report", False, f"unreadable report: {exc}")
            return
        check("bench_schema", report.get("schema_version") == 1, repr(report.get("schema_version")))
        check("physical_bench", report.get("evidence_kind") == "physical-bench", repr(report.get("evidence_kind")))
        check("not_simulation", report.get("simulation") is False, repr(report.get("simulation")))
        check("source_commit", report.get("source_commit") == SOURCE_COMMIT, str(report.get("source_commit", "missing")))
        check("generation", report.get("generation") == generation.value, str(report.get("generation", "missing")))

        identity = report.get("ecu_identity")
        hardware = report.get("bench_hardware")
        check("live_ecu_identity", isinstance(identity, dict) and any(str(value).strip() for value in identity.values()), "recorded" if isinstance(identity, dict) else "missing")
        check("bench_hardware", isinstance(hardware, dict) and all(str(hardware.get(key, "")).strip() for key in ("adapter", "power_supply", "ecu")), "recorded" if isinstance(hardware, dict) else "missing")

        performed = str(report.get("performed_at_utc", ""))
        try:
            timestamp = datetime.fromisoformat(performed.replace("Z", "+00:00"))
            timestamp_ok = timestamp.tzinfo is not None
        except ValueError:
            timestamp_ok = False
        check("timestamp", timestamp_ok, performed or "missing")
        check("operator", bool(str(report.get("operator", "")).strip()), "recorded" if report.get("operator") else "missing")

        voltage = report.get("voltage") if isinstance(report.get("voltage"), dict) else {}
        try:
            minimum = float(voltage.get("minimum_v"))
            maximum = float(voltage.get("maximum_v"))
            voltage_ok = 12.5 <= minimum <= maximum <= 15.0
        except (TypeError, ValueError):
            voltage_ok = False
        check("bench_voltage", voltage_ok, f"min={voltage.get('minimum_v')!r}, max={voltage.get('maximum_v')!r}")

        firmware = report.get("firmware") if isinstance(report.get("firmware"), dict) else {}
        input_hash = str(firmware.get("input_sha256", ""))
        readback_hash = str(firmware.get("post_recovery_readback_sha256", ""))
        firmware_ok = _is_sha256(input_hash) and input_hash == readback_hash
        check("recovery_readback", firmware_ok, "matching SHA-256" if firmware_ok else "missing or mismatched")

        loader_id = str(report.get("loader_id", ""))
        loader_hash = str(report.get("loader_sha256", ""))
        if generation is TrionicGeneration.T7:
            loader_ok = loader_id == "none" and loader_hash == "none"
        else:
            loader_ok = loader_id in loader_hashes and loader_hashes.get(loader_id) == loader_hash
        check("bench_loader", loader_ok, f"{loader_id}: {loader_hash}")

        scenarios = report.get("scenarios") if isinstance(report.get("scenarios"), dict) else {}
        bundle_root = path.resolve().parent
        for name in _REQUIRED_SCENARIOS[generation]:
            item = scenarios.get(name) if isinstance(scenarios.get(name), dict) else {}
            trace_name = str(item.get("trace", ""))
            expected_hash = str(item.get("trace_sha256", ""))
            trace_ok = False
            detail = "missing"
            if item.get("passed") is True and trace_name and _is_sha256(expected_hash):
                trace_path = (bundle_root / trace_name).resolve()
                try:
                    trace_path.relative_to(bundle_root)
                    actual_hash = hashlib.sha256(trace_path.read_bytes()).hexdigest()
                except (ValueError, OSError):
                    detail = "trace missing or outside bundle"
                else:
                    trace_ok = actual_hash == expected_hash
                    detail = f"{trace_name}: {actual_hash}"
            check(f"scenario:{name}", trace_ok, detail)


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value.lower())
