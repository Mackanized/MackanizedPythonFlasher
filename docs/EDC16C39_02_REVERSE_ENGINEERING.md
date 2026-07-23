# EDC16C39_02 reverse-engineering integration

The archived ETAS/ProF package contains real, useful implementation evidence.
PythonFlasher now models the parts that can be reproduced and tested without
guessing at missing transport behavior.

## Recovered and integrated

| Component | Archive evidence | PythonFlasher implementation | Confidence |
| --- | --- | --- | --- |
| CAN transport profile | `EDC16.cnf`: 500 kbit/s, request `0x7E0`, response `0x7E8` | `ProtocolFamily.KWP2000_ISOTP`, `EDC16C39` metadata | Archive-verified |
| Programming session | `DIAG_MODE 0x84` | `10 84` codec | Archive-verified parameter; payload is offline-only until trace replay |
| SecurityAccess | `SECURITY_ACCESS_MODE 0x05`, archived `SEED.DLL` | six-byte seed, four-byte key provider | Byte-exact against emulated DLL over generated vectors |
| Identification | `KWP2000_SERVICE 1`: `1A 8A` | identification payload codec | Archive-verified |
| Erase/check routines | local routines `02` and `01` | typed payload codecs | Archive-derived; exact physical response behavior unverified |
| Memory layout | distinct `ERASE`, `SOURCE`, and `DEST` areas | typed half-open areas | Archive-verified |
| Full program order | `prog_all.pri`, `flash.pri`, `seed_pa.pri` | immutable 19-phase plan | Archive-verified |
| Firmware checksum | archived `EPROM15.EXE`, info-block sentinels | native SUMMBIGEND inspection/correction | Fixed-point verified against a real 2 MiB fixture and executable oracle |
| Addressed reads | reverse-engineering candidate contract: `23 44 <addr32> <size32>` | strict physical ISO-TP client and semantic mock | Implemented for bench/replay; live layout not yet captured |
| Transfer framing | reverse-engineering candidate contract: `36 <counter> <data>`, `37` | strict counter/length state machine | Implemented for bench/replay; live packing not yet captured |
| Offline workflows | ETAS phase plan + semantic mock adapter | all three erases, four downloads, two resets/security exchanges, readback, failure injection | Complete simulation; not physical evidence |

## Implemented execution paths

The default protocol factory now selects an EDC16-specific client instead of
the generic GMLAN writer:

- The explicitly selected mock ECU runs the immutable 19-phase plan. Erase
  changes virtual flash to `0xFF`, each RequestDownload is bound to its exact
  destination, block counters and transfer lengths are checked, and every
  programmed area is read back byte-for-byte.
- A physical KWP2000/ISO-TP client implements connection enforcement,
  level-05 SecurityAccess, session `0x84`, local-ID `0x8A` identification,
  candidate addressed reads, area-specific erase/download, TransferData,
  transfer exit, routine parsing, reset, and reconnect detection.
- The application delegates full images to the EDC16 coordinator. Partial
  calibration simulation remains non-destructive and does not pretend to be
  the archive's combined data/variant physical erase flow.

The physical client is intentionally available for non-destructive read and
synthetic/captured replay development while `EDC16C39.PHYSICAL_PROGRAMMING_IMPLEMENTED`
and physical write capabilities remain false. Consequently, normal application
preflight rejects physical erase before any programming-session request.

## Exact full-program sequence

`prog_all.pri` does not describe one flat download. It requires:

1. Connect, request level-05 security, then start programming session `0x84`.
2. Erase PA `0x010000..0x030000`; program and verify `0x010000..0x02FF00`.
3. Reset the ECU, wait for it to return, request security again, and start a
   new programming session.
4. Erase code `0x030000..0x150000` and the combined external data/variant
   erase area `0x150000..0x200000`.
5. Program and verify code `0x030000..0x150000`.
6. Program and verify calibration data `0x1C0000..0x1FE000`.
7. Program and verify variant data `0x150000..0x1C0000`.
8. Reset the ECU.

The PA destination ends at `0x02FF00`, even though its erase page ends at
`0x030000`. The data and variant destinations are separate even though they
share one erase area. Collapsing either distinction can program bytes that are
not represented by the source image.

## Checksum result

The checksum is stored big-endian and is calculated per self-describing info
block:

```text
checksum = 0xCAFEAFFE - (0xFADECAFE + sum(big-endian 32-bit words)) mod 2^32
```

Info blocks can be nested and can cross-store a predecessor's checksum. The
implementation discovers the dependency chain from each 2 MiB image and writes
inner checksums before regions that include those checksum fields.

## Still missing before physical erase/write

- A captured CAN or K-line session proving ProF's exact TransferData packing,
  block counters, negotiated size, pending responses, timing, and retry rules.
- A live level-05 seed/key exchange proving the archived DLL matches the exact
  ECU software/hardware combination. It is not the GM SPS level-01 algorithm.
- Strict identification values for supported hardware/software variants.
- Executable BDM/boot-mode recovery and interrupted-erase/transfer bench tests.
- Reverse engineering of `SwitchOver.dll` if series-to-application conversion
  is required. Its local-ID `0xFA` exchange is documented, but its request/reply
  transformation remains opaque.

## `SwitchOver.dll` static map

The remaining DLL is no longer an undifferentiated black box. Static analysis
establishes the following call boundary:

- PE32/i386 Bosch build dated 2003-03-11; SHA-256
  `7b041726f8133d11e6b21445d3fbf346b341caa03428e8be68f21df0101b3eb2`.
- Export `Request` is at RVA `0x1220`. It accepts the single `request.bin`
  argument produced by `READ_MEMORY_BY_LOCALID($FA, ...)`, parses that file,
  and reports the current application/series state.
- Export `Reply` is at RVA `0x12C0`. Its parser accepts three or four arguments,
  reads `CRYPTDIR` attestation/key material, and generates `reply0.bin` through
  `reply3.bin` for the four `WRITE_MEMORY_BY_LOCALID($FA, ...)` phases.
- Embedded validation paths cover an ECU application flag, an attestation-empty
  flag, public-key name length, record identifiers, serial number, and the
  states “series mode”, “application mode”, and “ready to switch”.
- The DLL imports the ETAS `G_ErrorManager` framework, uses C++ exception
  support, and performs file and environment I/O. It is therefore materially
  larger than the pure `SEED.DLL` function and cannot be replaced by copying a
  small arithmetic loop.

`switch_2.pri` has the `Reply` invocation commented out while still consuming
the four reply files. That means the profiles alone do not prove when or where
those files are generated in the complete ETAS workflow. A clean native port
needs either captured request/reply files or a deterministic emulation harness
for the `Request` and `Reply` exports. Ordinary PA/code/data/variant flashing
does not call this switchover path.

For those reasons, the semantic simulator and candidate protocol state machine
are complete for application, replay, and bench-development testing, while
physical EDC16C39 write capability remains fail-closed.
