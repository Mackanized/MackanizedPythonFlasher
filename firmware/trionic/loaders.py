"""Integrity-checked Trionic loader artifact catalog.

The loader bytes are imported verbatim from the pinned upstream source.  This
module never uploads or executes them; it only verifies provenance metadata,
file length, SHA-256, and (for T5) Motorola S-record checksums.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Tuple


class LoaderId:
    """Canonical loader artifact identifiers, to keep call sites and the
    manifest's ``id`` field from drifting apart via a typo'd string literal.
    """

    T5_LOADER = "t5-loader"
    T8_STOCK_READ = "t8-stock-read"
    T8_STOCK_PROGRAM = "t8-stock-program"
    T8_LEGION = "t8-legion"


PINNED_COMMIT = "4d4c332a166f89c1a9627cd3c9c231fe5a0ed0b9"
PINNED_ARTIFACTS = {
    LoaderId.T5_LOADER: (4483, "51feaa6e941ab21b7a335a775770b95edabfdc12d14261d0e03a2b12f8cd0f84"),
    LoaderId.T8_STOCK_READ: (16667, "0dca5077278b359ec472c0cf9633333c0c4fd44ae40bcfd4c13721ba6ab466c6"),
    LoaderId.T8_STOCK_PROGRAM: (16667, "2dbc646d059dec84b4818d1541610c13450f7c4fdffe0cf25bb35e90b50bcd76"),
    LoaderId.T8_LEGION: (16667, "0f74eeea85b1ae21d405ae071d481b25d693b6d0026b1ae3e96a6b2e28268778"),
}


class LoaderIntegrityError(ValueError):
    """A loader is missing, malformed, or differs from its pinned digest."""


@dataclass(frozen=True)
class LoaderArtifact:
    identifier: str
    generation: str
    purpose: str
    format: str
    path: Path
    size: int
    sha256: str
    source_file: str
    source_symbol: str
    source_commit: str
    license_evidence: str

    def read_verified(self) -> bytes:
        try:
            payload = self.path.read_bytes()
        except OSError as exc:
            raise LoaderIntegrityError(f"Loader {self.identifier} cannot be read: {exc}") from exc
        actual = hashlib.sha256(payload).hexdigest()
        if len(payload) != self.size:
            raise LoaderIntegrityError(
                f"Loader {self.identifier} length mismatch: expected {self.size}, got {len(payload)}"
            )
        if actual != self.sha256:
            raise LoaderIntegrityError(
                f"Loader {self.identifier} SHA-256 mismatch: expected {self.sha256}, got {actual}"
            )
        if self.format == "motorola-s-record":
            _validate_s_records(payload, self.identifier)
        elif self.generation == "t8":
            # The reference uploads 70 groups of 34 seven-byte CF payloads,
            # followed by one final seven-byte payload.
            expected_payloads = 70 * 34 + 1
            if len(payload) % 7 or len(payload) // 7 != expected_payloads:
                raise LoaderIntegrityError(
                    f"Loader {self.identifier} does not match the pinned T8 upload chunk plan"
                )
        return payload


class LoaderCatalog:
    """Load and verify the generated loader manifest and every artifact."""

    MANIFEST_NAME = "manifest.json"

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).with_name("loaders")
        self._manifest = self._read_manifest()

    @property
    def provenance(self) -> Mapping[str, Any]:
        return dict(self._manifest["provenance"])

    def artifacts(self) -> Tuple[LoaderArtifact, ...]:
        result = []
        for item in self._manifest["artifacts"]:
            identifier = str(item["id"])
            pinned = PINNED_ARTIFACTS.get(identifier)
            actual_contract = (int(item["size"]), str(item["sha256"]))
            if pinned is None or pinned != actual_contract:
                raise LoaderIntegrityError(f"Loader manifest contract differs from pinned artifact {identifier}")
            result.append(
                LoaderArtifact(
                    identifier=identifier,
                    generation=str(item["generation"]),
                    purpose=str(item["purpose"]),
                    format=str(item["format"]),
                    path=self.root / str(item["filename"]),
                    size=int(item["size"]),
                    sha256=str(item["sha256"]),
                    source_file=str(item["source_file"]),
                    source_symbol=str(item["source_symbol"]),
                    source_commit=str(self._manifest["provenance"]["commit"]),
                    license_evidence=str(self._manifest["provenance"]["license_evidence"]),
                )
            )
        return tuple(result)

    def get(self, identifier: str) -> LoaderArtifact:
        matches = tuple(item for item in self.artifacts() if item.identifier == identifier)
        if len(matches) != 1:
            raise KeyError(f"Unknown Trionic loader artifact: {identifier}")
        return matches[0]

    def validate_all(self) -> Tuple[LoaderArtifact, ...]:
        artifacts = self.artifacts()
        if {item.identifier for item in artifacts} != set(PINNED_ARTIFACTS):
            raise LoaderIntegrityError("Trionic loader manifest does not contain the complete pinned artifact set")
        if self._manifest["provenance"].get("commit") != PINNED_COMMIT:
            raise LoaderIntegrityError("Trionic loader manifest source commit differs from the pinned commit")
        for artifact in artifacts:
            artifact.read_verified()
        return artifacts

    def _read_manifest(self) -> Mapping[str, Any]:
        path = self.root / self.MANIFEST_NAME
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LoaderIntegrityError(f"Invalid Trionic loader manifest {path}: {exc}") from exc
        if manifest.get("schema_version") != 1:
            raise LoaderIntegrityError("Unsupported Trionic loader manifest schema")
        provenance = manifest.get("provenance")
        artifacts = manifest.get("artifacts")
        if not isinstance(provenance, dict) or not isinstance(artifacts, list):
            raise LoaderIntegrityError("Trionic loader manifest is missing provenance or artifacts")
        return manifest


@lru_cache(maxsize=1)
def get_default_catalog() -> LoaderCatalog:
    """Shared :class:`LoaderCatalog` for the standard on-disk loader directory.

    Every call site that doesn't need a custom ``root`` (i.e. everything
    except tests) should use this instead of constructing ``LoaderCatalog()``
    directly, so the manifest is only read and parsed once per process.
    """
    return LoaderCatalog()


def _validate_s_records(payload: bytes, identifier: str) -> None:
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise LoaderIntegrityError(f"Loader {identifier} is not ASCII S-record data") from exc
    if not lines or not any(line.startswith(("S7", "S8", "S9")) for line in lines):
        raise LoaderIntegrityError(f"Loader {identifier} has no S-record termination record")
    data_records = 0
    termination_records = 0
    for line_number, line in enumerate(lines, 1):
        if not line:
            continue
        if len(line) < 6 or not line.startswith("S") or line[1] not in "0123456789":
            raise LoaderIntegrityError(f"Loader {identifier} has malformed S-record line {line_number}")
        try:
            record = bytes.fromhex(line[2:])
        except ValueError as exc:
            raise LoaderIntegrityError(
                f"Loader {identifier} has non-hex S-record line {line_number}"
            ) from exc
        if not record or record[0] != len(record) - 1:
            raise LoaderIntegrityError(f"Loader {identifier} byte count fails at line {line_number}")
        if (sum(record) & 0xFF) != 0xFF:
            raise LoaderIntegrityError(f"Loader {identifier} checksum fails at line {line_number}")
        record_type = line[1]
        if record_type in "123":
            address_length = {"1": 2, "2": 3, "3": 4}[record_type]
            if record[0] <= address_length:
                raise LoaderIntegrityError(f"Loader {identifier} has empty data record at line {line_number}")
            data_records += 1
        elif record_type in "789":
            termination_records += 1
    if data_records == 0 or termination_records != 1:
        raise LoaderIntegrityError(
            f"Loader {identifier} requires data records and exactly one termination record"
        )
