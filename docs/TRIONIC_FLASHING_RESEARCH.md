# Trionic 5/7/8 Flashing Research and Integration Boundary

## Scope and provenance

This document records a source-level interoperability study of
[`roffe/Trionic`](https://github.com/roffe/Trionic) at commit
`4d4c332a166f89c1a9627cd3c9c231fe5a0ed0b9` (2025-12-28).

Evidence classification: **strongly inferred**, not OEM-verified. The user
confirmed MIT licensing, while the pinned source checkout did not contain a
detectable standalone license file. T5/T8 loader artifacts are now imported
verbatim with source-file and payload SHA-256 values, attribution, and an
explicit record that the license provenance is user supplied.

The implementation now enables owner-authorized physical Trionic programming
through the normal runtime preflight. T5, T7, and T8 expose write regions and
generation-specific clients, plus exact semantic mocks and replay coverage.
Preflight still blocks writes unless the adapter is connected, live identity is
compatible, voltage evidence is fresh, a verified backup is confirmed, the
firmware checksum passes, protected ranges are excluded, and readback
verification is available. Simulator and synthetic replay success are not
bench evidence.

## Executive findings

T5, T7, and T8 are not interchangeable GMLAN configurations:

| Family | Transport | Image | Read/write unit | Programming boundary |
|---|---|---:|---:|---|
| T5.2 | Native raw-CAN SRAM loader, `0x005` → `0x00C` | 128 KiB | 6-byte reads / 128-byte writes | File image maps to physical `0x60000..0x7FFFF` |
| T5.5 | Native raw-CAN SRAM loader, `0x005` → `0x00C` | 256 KiB | 6-byte reads / 128-byte writes | File image maps to physical `0x40000..0x7FFFF` |
| T7 | Saab KWP2000 row framing over CAN | 512 KiB | 64-byte reads / 128-byte writes | Programs `0x00000..0x7AFFF` and `0x7FE00..0x7FFFF`; preserves the middle gap |
| T8 | GMLAN/ISO-TP plus uploaded SRAM loader | 1 MiB | 128-byte loader reads; stock writer uses encoded chunks | Stock flow starts application programming at `0x020000`; boot/NVDM/HWIO require separate high-risk policy |

The former generic `RequestDownload → TransferData(address) → TransferExit`
model is not a safe physical implementation for all three families.

## Trionic 5

### Observed command channel

- Request CAN ID: `0x005`
- Response CAN ID: `0x00C`
- `A5 00 aa aa aa ll 00 00`: select a 24-bit address and byte count.
- `oo dd dd dd dd dd dd dd`: transfer up to seven bytes with block offset `oo`.
- `C1 00 aa aa aa 00 00 00`: jump to an SRAM entry point.
- `C0 ...`: erase flash; operation may take up to approximately 60 seconds.
- `C7 aa aa aa aa 00 00 00`: read six bytes from a 32-bit address.
- `C8 ...`: ask the loader to calculate/report flash checksum.
- `C2 ...`: reset/exit loader.

Acknowledgements echo the command or data offset and report status `0x00`.
Every echo and status must be checked. Blank `0xFF` blocks may be skipped only
after the erase result is known and the skipped bytes are represented in the
verification plan.

### Image mapping and checksum

- T5.2 accepts a 128 KiB image and maps it at physical `0x60000`.
- T5.5 accepts a 256 KiB image and maps it at physical `0x40000`.
- A 128 KiB image may be duplicated in a T5.5 device in the reference tool,
  but PythonFlasher will require an explicit conversion operation rather than
  silently repeating the file.
- The final four bytes store a big-endian 32-bit additive checksum.
- A reverse footer container identifies the last used address; malformed or
  out-of-range pointers fail closed.

### Bench validation still required

- Bench traces for every command, timeout, status byte, flash chip variant,
  and reset outcome.
- Power interruption tests before/during erase and every programming window.
- T5.2/T5.5 hardware identity rules that prevent accidental cross-flashing.

## Trionic 7

### KWP2000-over-CAN transport

T7 does not use ISO-TP. It wraps length-prefixed KWP payloads into six-byte
rows:

- Session start: `0x220` request, `0x238` response.
- KWP request rows: `0x240`.
- KWP response rows: `0x258`.
- Per-row acknowledgement: `0x266`.
- A single VIN request is `40 A1 02 1A 90 00 00 00`.
- Response rows use `C? BF` for the first row and `8? BF` for continuations;
  the tester acknowledges each row with `40 A1 3F 8? 00`.

Rows must be complete and strictly ordered. Timeout, a bad row number, or a
truncated KWP length is a transport failure—not an empty response.

### Flash sequence

1. Start the proprietary KWP session.
2. Request SecurityAccess seed at level `0x05`; send key at `0x06`.
3. Request a fresh seed for each of the two observed key variants and stop on
   lockout/delay negative responses.
4. Validate the T7 FW, F2, and FB checksums and footer metadata.
5. Run erase routine `31 52` to positive `71` with a bounded deadline.
6. Run erase routine `31 53` to positive `71` with a bounded deadline.
7. Confirm with TesterPresent parameters `3E 53`.
8. Request download for `0x00000..0x7AFFF`, transfer 128-byte blocks.
9. Preserve `0x7B000..0x7FDFF`.
10. Request download for `0x7FE00..0x7FFFF`, transfer 128-byte blocks.
11. Read back both programmed ranges and verify byte-for-byte.
12. Stop the diagnostic session without blindly resetting the throttle ECU.

The reference implementation retries SecurityAccess and some transfers in
ways that are too permissive for an OEM-grade tool. PythonFlasher will use a
single trace-selected algorithm, an attempt budget, absolute deadlines, and no
automatic erase retry after state becomes uncertain.

## Trionic 8

### Normal programming entry

The observed normal flow uses physical `0x7E0/0x7E8` plus functional traffic:

1. Enter programming/diagnostic session.
2. Disable normal communication.
3. Report programmed state (`A2`).
4. Request/enable programming mode (`A5 01`, then `A5 03`).
5. Request SecurityAccess `01`, calculate a 16-bit key, submit at `02`.
6. Request download and upload an SRAM loader at `0x102400`.
7. Start it at the observed entry point near `0x102460` (loader-specific).
8. Erase selected partitions.
9. Program encoded blocks.
10. Verify using loader MD5/partition evidence and readback.
11. Ask the loader to exit, reconnect, and validate ECU identity.

The T8 transfer encoding repeats XOR bytes `39 68 77 6D 47 39`. The known
SecurityAccess vector `seed 5F94 → key 5C84` is covered by tests.

### Partition map

| Index | Range | Role | Default policy |
|---:|---|---|---|
| 0 | `0x000000..0x003FFF` | Boot | Protected |
| 1 | `0x004000..0x005FFF` | NVDM | Protected; VIN/key risk |
| 2 | `0x006000..0x007FFF` | NVDM | Protected; VIN/key risk |
| 3 | `0x008000..0x01FFFF` | HWIO/system | Protected |
| 4 | `0x020000..0x03FFFF` | Application | Simulator-writeable |
| 5 | `0x040000..0x05FFFF` | Application | Simulator-writeable |
| 6 | `0x060000..0x07FFFF` | Application | Simulator-writeable |
| 7 | `0x080000..0x0BFFFF` | Application | Simulator-writeable |
| 8 | `0x0C0000..0x0FFFFF` | Application | Simulator-writeable |

The pointer at `0x20140` identifies the checksum/header area and is used to
derive a bounded last-used address with a `0x200` margin. PythonFlasher now
validates the transformed-MD5 layer and the encoded layer-2 metadata/checksum,
with malformed pointer and corruption fixtures. Physical programming is
enabled through preflight; manual bench recovery evidence is still required
before treating a setup as proven.

### Recovery

The reference recovery path uses functional request ID `0x011`, recovery
response `0x311`, checks programmed state, re-enters programming, authenticates,
uploads a loader, and then resumes a complete verified write. Recovery is a
separate operation. It must never be entered merely because a normal request
timed out.

## Implemented in PythonFlasher

- Typed T5.2, T5.5, T7, and T8 profiles with provenance and evidence status.
- Registry-visible T5.2/T5.5/T7/T8 ECU definitions.
- Separate protocol families for T5 native loader and T7 KWP rows.
- Strict T5 command, T7 row-framing, and T8 block-coding primitives.
- Known-answer T8 SecurityAccess coverage and guarded T7 key candidates.
- Read/write policy separation so the T7 protected gap remains readable.
- Imported T5 and T8 loader artifacts with pinned source/payload hashes and
  S-record validation.
- Complete T7 FW/F2/FB and T8 layer-1/layer-2 checksum strategies, immutable
  correction helpers, and deterministic known-answer fixtures.
- Strict CAN replay adapter plus clearly labelled synthetic-reference T5
  loader, T7 KWP security, and T8 recovery-entry traces.
- A native T5 client that verifies and uploads the pinned S-record loader,
  reads six-byte C7 chunks, erases once, skips erased `0xFF` blocks, checks every
  acknowledgement/status, requests C8 verification, reads back, and exits C2.
- A T7 client that implements the proprietary session, complete row/ACK
  transport, one configured security-key variant, bounded 0x52/0x53 erase,
  primary/footer downloads, protected-gap preservation, readback, and session
  stop.
- A T8 client that implements the normal diagnostic bootstrap, stock read or
  program loader upload at `0x102400`, execution at `0x102460`, four-byte loader
  transfer addresses, encoded application blocks, readback, loader exit, and
  explicit `0x011/0x311` recovery session/security entry.
- Generation-aware managed semantic simulation for T5/T7/T8, including exact
  erase boundaries, sparse T5 writes, T7 gap preservation, T8 boot preservation,
  checksum rejection, readback, progress beyond 25%, and phase failure injection.
- Client-driven synthetic replay for the T5 loader handshake, T7 session and
  SecurityAccess exchange, and T8 recovery entry.
- Factory construction of all three physical clients with physical write
  capabilities, regions, and recovery strategies declared.

## Hardware test gates

The code now allows physical Trionic writes, but a bench setup should not be
treated as validated until all of these are present:

1. Review the recorded user-confirmed MIT provenance against any later
   upstream license publication.
2. Independent known-good firmware checksum vectors (synthetic vectors pass).
3. Captured request/response traces for normal read, normal write, negative
   responses, response-pending, and recovery.
4. Bench ECU tests with current-limited stable power and voltage telemetry.
5. Power interruption matrix and documented recovery outcome.
6. Identity/compatibility policy for each hardware/software variant.
7. Post-flash ECU verification plus byte-for-byte readback.
8. Explicit opt-in hardware test markers; never part of the default test run.

The executable evidence validator and scenario requirements are documented in
[`TRIONIC_BENCH_RECOVERY.md`](TRIONIC_BENCH_RECOVERY.md). A valid evidence
bundle records engineering evidence; it does not toggle physical writes at
runtime.

The simulator is for workflow and failure-path testing only. It must not be
presented as evidence that a physical ECU has been flashed successfully.
