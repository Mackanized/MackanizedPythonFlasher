# Trionic physical bench recovery release gate

Physical T5, T7, and T8 write support is enabled for owner-authorized bench
testing through the normal programming preflight. Loader integrity, software
checksum tests, exact mocks, and client-level synthetic replay are necessary
but do not establish that a specific ECU, adapter, power supply, or recovery
sequence is safe.

The factory exposes the physical clients so an engineer can capture read,
write, and recovery traces. The application still requires a connected
adapter, live identity, fresh voltage evidence, checksum validation, operator
authorization, backup confirmation, protected-range exclusion, and readback
verification before erase.

## Bench rules

- Use an owner-authorized spare ECU on a fused, current-limited bench supply.
- Record ECU identity before any erase or write.
- Capture raw CAN traffic for every scenario; a textual operator note is not a
  substitute for a trace.
- Keep protected T7/T8 regions byte-identical and prove this by pre/post hashes.
- Do not test an interruption by removing power during an undocumented unsafe
  window. Use the bench plan approved for the ECU hardware revision.
- Preserve power after an unknown erase/transfer outcome and enter the defined
  recovery path. Never retry erase blindly.
- A recovered full readback must have the same SHA-256 as the programmed image.

## Required scenarios

T5.2/T5.5 require identification, loader upload/start, interrupted-transfer
recovery, full post-recovery readback, and post-reset reconnection.

T7 requires identification, checksum preflight, preservation of
`0x7B000..0x7FE00`, interrupted-transfer recovery, and post-reset reconnection.

T8 requires identification, loader upload/start, recovery entry on
`0x011/0x311`, interrupted-erase recovery, interrupted-transfer recovery,
preservation of boot/NVDM/HWIO partitions, full post-recovery readback, and
post-reset reconnection.

## Evidence bundle

Create a JSON report with `schema_version: 1`, `evidence_kind:
"physical-bench"`, `simulation: false`, the pinned source commit, generation,
operator and UTC timestamp, live ECU identity, adapter/power-supply/ECU bench
identifiers, observed minimum/maximum voltage, loader ID and manifest SHA-256,
and matching input/readback firmware SHA-256 values.

Each required `scenarios` entry must contain `passed: true`, a trace path
relative to the report, and that trace file's SHA-256. Validate the bundle with:

```bash
python3 scripts/validate_trionic_bench.py t8 /path/to/report.json --json
```

A passing result says `eligible_for_engineering_review: true`. Evidence files
document bench confidence only; they do not toggle physical writes at runtime.
