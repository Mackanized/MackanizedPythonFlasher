# Bosch MED17/EDC17 checksum support

## Provenance

The parser and checksum algorithms are derived from the MIT-licensed
[`ConnorHowell/medc17-checksum-tool`](https://github.com/ConnorHowell/medc17-checksum-tool)
at commit `4ebf4c3216aebc6112de5d1aba3b7b0b62c20628`.

The upstream project identifies Bosch blocks by their little-endian headers,
TriCore `0x80000000..0x8FFFFFFF` memory addresses, checksum descriptor tables,
and a terminal `DEADBEEF` marker. PythonFlasher rejects truncated tables,
out-of-block ranges, non-dword-aligned regions, unknown algorithms, and images
with no authoritative checksum structures.

## Implemented algorithms

| ID | Algorithm | Processing | Validation target |
|---:|---|---|---|
| `0x00` | CRC32 | Reflected `0xEDB88320`, little-endian dwords, no final XOR | `0x35015001` |
| `0x01` | ADD32 | Little-endian dword sum with 32-bit wrap | Descriptor expected value |
| `0x10` | ADD16 | Little-endian word sum; terminal word occupies the high half | Descriptor expected value |

ADD32 and ADD16 correction returns a modified copy and changes only the final
adjustment dword of an invalid covered range. Every result is reparsed and
revalidated.

CRC32 is inspection-only. The referenced correction path combines CRC
adjustment with RSA signature forging. PythonFlasher does not implement
signature forging or CVN manipulation.

## Evidence limitations

The upstream author states that testing is primarily calibration-focused and
that variant datasets, code-section changes, and code-monitoring checksums need
additional validation. Therefore:

- EDC17C19 physical writes remain disabled.
- A full image must identify itself as `EDC17_C19` before the ECU module accepts
  its checksum result.
- Software vectors prove parity with the pinned implementation, not physical
  ECU acceptance.
- Known-good stock/modified C19 pairs and physical readback evidence are still
  required before programming support can be released.
