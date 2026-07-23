"""Explain whether an ECU definition is eligible for physical programming.

This module is intentionally read-only: it reports the executable contract and
never turns a simulator profile, environment variable, or evidence file into a
hardware-write release.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from ecus.base_ecu import BaseECU


@dataclass(frozen=True)
class ReadinessBlocker:
    code: str
    detail: str


@dataclass(frozen=True)
class PhysicalWriteReadiness:
    ecu_name: str
    region_name: Optional[str]
    ready: bool
    blockers: Tuple[ReadinessBlocker, ...]

    @property
    def summary(self) -> str:
        if self.ready:
            return "physical programming contract is complete"
        return "; ".join(f"{item.code}: {item.detail}" for item in self.blockers)

    def as_dict(self) -> dict:
        return {
            "ecu": self.ecu_name,
            "region": self.region_name,
            "ready": self.ready,
            "blockers": [
                {"code": item.code, "detail": item.detail}
                for item in self.blockers
            ],
        }


def assess_physical_write_readiness(
    ecu: BaseECU,
    region_name: Optional[str] = None,
) -> PhysicalWriteReadiness:
    """Return every release blocker for *ecu* without touching hardware."""

    blockers = []

    def require(code: str, passed: bool, detail: str) -> None:
        if not passed:
            blockers.append(ReadinessBlocker(code, detail))

    capabilities = ecu.CAPABILITIES
    write_regions = ecu.get_write_regions()
    if region_name is None:
        capability = (
            capabilities.supports_full_write
            or capabilities.supports_calibration_write
        )
        region_declared = bool(write_regions)
    else:
        capability = (
            capabilities.supports_full_write
            if region_name == "full"
            else capabilities.supports_calibration_write
        )
        region_declared = region_name in write_regions

    require(
        "physical_implementation",
        ecu.PHYSICAL_PROGRAMMING_IMPLEMENTED,
        (
            "candidate erase/transfer/verify client exists, but captured replay and "
            "bench recovery have not released it"
            if ecu.PHYSICAL_PROGRAMMING_CANDIDATE_IMPLEMENTED
            else "ECU-specific physical erase/transfer/verify client is not implemented"
        ),
    )
    require(
        "write_capability",
        capability,
        capabilities.development_status or "physical write capability is not released",
    )
    require(
        "write_region",
        region_declared,
        region_name or "no physical write regions are declared",
    )
    require(
        "programming_strategy",
        bool(ecu.PROGRAMMING_STRATEGY.strip()),
        "no ECU-specific programming strategy is declared",
    )
    require(
        "checksum_strategy",
        bool(ecu.CHECKSUM_STRATEGY.strip()),
        "no fail-closed programming checksum strategy is declared",
    )
    require(
        "identity_policy",
        type(ecu).is_identity_compatible is not BaseECU.is_identity_compatible,
        "live ECU identity compatibility policy is not implemented",
    )
    require(
        "recovery_strategy",
        bool(ecu.RECOVERY_STRATEGY.strip()),
        "interrupted-write bench recovery strategy is not declared",
    )
    require(
        "recovery_capability",
        capabilities.supports_recovery,
        "recovery capability is not released",
    )
    require(
        "engineering_evidence",
        bool(capabilities.evidence_reference.strip()),
        "trace/checksum/bench evidence reference is missing",
    )

    return PhysicalWriteReadiness(
        ecu_name=ecu.NAME,
        region_name=region_name,
        ready=not blockers,
        blockers=tuple(blockers),
    )
