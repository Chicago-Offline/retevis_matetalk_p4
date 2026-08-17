# P4 CPS `.dat` save-file format

Notes on the **CPS save file** produced by the OEM programming software — the
container, not the codeplug byte map.

## 🔴 For the codeplug byte map, use p64tool

**[`oetiker/p64tool` → `docs/codeplug-format.md`](https://github.com/oetiker/p64tool/blob/main/docs/codeplug-format.md)
is the authoritative reference** for channel/contact/zone/scan-list/encryption
record layouts, and it is better sourced than anything derivable from a single
save file: decompiled vendor CPS cross-checked against live hardware dumps, with
the dump winning on conflict.

Do not re-derive record offsets here. Look them up there, and send corrections
upstream.

This document covers only the part p64tool does **not** describe: the ASCII
wrapper the CPS writes to disk. p64tool reads regions off the serial link, so it
never sees this file format.

## The save file

Example: `cps/cps_saves/retevis_matetalkp4_oem_cps_baseline_factory_20260812.dat`
— an OEM CPS v1.5 read of a factory-fresh, unmodified radio (10,818 bytes,
85 lines).

### It is ASCII text, not a binary image

CRLF line endings. Hex bytes are written as space-separated ASCII pairs. Tooling
that assumes a binary blob fails immediately.

```
Model=P4 V1.5
010001 00016=50 00 34 00 20 00 56 00 31 00 2E 00 32 00 00 00 FF FF ...
```

Line 1 is a model/version header. Every other non-blank line is one record.
Blank lines separate sections and carry no data.

### Line grammar

```
<6-char record key> <5-digit offset>=<hex bytes, space separated, trailing space>
```

⚠️ **The record key is exactly 6 characters and may contain letters *and
spaces*** — `010001`, `02CODE`, `02 KEY`, `08CH01`, `KL0001`. A regex like
`^([A-Z]+)(\d+)` matches only a fraction of the file and **silently drops the
rest**. Anchoring on exactly 6 characters parses 68/68 records with zero
failures.

⚠️ **The 5-digit field is a byte OFFSET, not a length.** Reading it as a length
yields a 25-of-25 "mismatch" — which is the tell that the assumption is wrong,
not the file. Within a section the offsets advance by the previous record's byte
count (72 per record across the channel block).

```python
import re
REC = re.compile(r'^(.{6}) (\d{5})=(.*?)\s*$')   # key, offset, hex payload
```

### Key prefix → p64tool region

The 2-character prefix maps onto p64tool's regions, and the trailing "E-number"
mnemonic matches the list-type ids documented there (`E4`=contacts,
`E5`=RX-groups, `EM`=emergency, `CH`=channels).

| Key prefix | Records | p64tool region |
|---|---|---|
| `01` | 10 | `r01` device identity |
| `02` | 10 | `r02` general settings + encryption keys |
| `03` | 1 | `r03` DMR network/service |
| `04` | 2 | `r04` contacts + RX-group lists |
| `05` | 2 | `r05` emergency systems |
| `06` | 1 | `r06` scan lists |
| `07` | 2 | `r07` zones |
| `08` | **32** | `r08` channel table |
| `0A` | 1 | `r0A` alerts / man-down |
| `KL` | 6 | `rKL` (empty on a stock radio) |
| `ML` | 1 | `rML` quick-text messages |

### Record payloads vs. the serial regions — verified

**Record payloads are the bytes p64tool documents, but the `.dat` offset is not
the region offset.** The mapping is:

```
region_offset = dat_offset - 15
```

Verified against a full OEM CPS serial capture of the same factory-fresh radio
(`cps/cps_serial_dumps/P4_OEM_BASELINE_CPS_READ_DUMP.txt`): **54 of 61 records
match byte-for-byte** at that shift.

| Key prefix | Region | Records matching |
|---|---|---|
| `01` | `0100` | 6/10 |
| `02` | `0200` | 8/10 |
| `03` | `0300` | 0/1 |
| `04` | `0400` | 2/2 ✅ |
| `05` | `0500` | 2/2 ✅ |
| `06` | `0600` | 1/1 ✅ |
| `07` | `0700` | 2/2 ✅ |
| `08` | `0800` | **32/32 ✅** |
| `0A` | `0a00` | 1/1 ✅ |

So a `08CHnn` payload *is* a 72-byte channel record and p64tool's field offsets
apply within it — byte 32 channel type, 36–39 RX frequency, and so on per
`docs/codeplug-format.md`.

⚠️ **The `.dat` is NOT a byte-identical dump of the serial regions.** An earlier
revision of this document claimed it was, on the strength of three spot-checked
fields that happened to land in the clean regions. Two things break that claim:

**1. CPS-authored metadata the radio never sends.** These records exist in the
`.dat` with no serial counterpart, or differ from what the radio reports:

| Record | `.dat` | serial | what it is |
|---|---|---|---|
| `010004` | `20260812144038` | `20260402153335` | save timestamp |
| `010005` | `2026-04-20` | `2025/7/14` | date — **and a different format** |
| `010007` | `P4 V1.5` | all-`FF` | CPS version, stamped on save only |
| `010008` | `1.0.0.0` + build date | `1.0.0.0` + `FF` | fw version matches; build date is `.dat`-only |

**2. Two single-byte differences that are NOT yet explained:**

```
020100   .dat 8f …           serial f8 …
020300   .dat 03 01 01 00    serial 03 01 0a 00
```

Could be CPS normalising on save, or live radio state differing from saved
state. **Unresolved — do not guess at these.**

**3. Region `03` length mismatch.** `030000` is 34 bytes in the `.dat`; serial
region `0300` is only 33 bytes total. The `.dat` record is one byte longer than
the entire region it supposedly mirrors.

🔴 **Method note.** Deriving this took three attempts: assuming the `.dat` offset
was the region offset gave 0/61, and assuming −1 also gave 0/61. The `-15` shift
was only found by *searching* for each record's bytes inside the region rather
than asserting a mapping. The tell was that the first mismatch landed at offset
16 in **every single region** — a constant failure offset across all regions
means the parser is wrong, not the data.

⚠️ Read the bookkeeping fields at 66–67 and 70–71 as **u16 LE**, per p64tool.
Reading them as single bytes happens to work on a 32-channel radio and breaks
above 255.

## What the CPS reads that p64tool does not

The same serial capture shows CPS issuing **14 region reads**; p64tool's
`REGIONS` table covers **9** of them. Region selectors are at `cmd[14..15]` of
each `0x4D` command.

⚠️ **CPS does not read selectors in numeric order** — it reads `02 00` *before*
`01 00`. Assuming numeric order makes the first two regions look transposed.

Observed order, with reply sizes in bytes:

```
CONNECT    → 149
op=0x00    → 52       ← not read by p64tool (54-byte command)
02 00      → 2187
01 00      → 275
03 00      → 51
04 00      → 10323
05 00      → 791
06 00      → 2899
07 00      → 1107
08 00      → 18451
ff ff      → 619
32 00      → 51
0a 00      → 53
00 01      → 43       ← not read by p64tool
01 01      → 16531    ← not read by p64tool, 2nd-largest region
DISCONNECT → 19
```

Not reading a region is not necessarily a defect — p64tool claims parity for the
settings it *exposes*, and these may be deliberately ignored. But **`01 01` is
16,531 bytes and nothing is known about its contents.**

## Protocol confirmation

The same capture confirms p64tool's `PROTOCOL.md` is accurate for this radio:

- Connect frame is **byte-identical** to p64tool's, all 38 bytes:
  `5F5F 1E00 0023 0026 0200 4011 1200` + 20 × `00` + `FFFF55AA`
- Reply is 149 bytes, prefix `5F5F 8F00 0026 0023 0200 5011`, exactly as
  documented
- UTF-16LE fields in the reply decode as firmware `V1.0.0.0` and serial
  `428734460100152`

The capture was taken with **CPS v1.5**; p64tool was reverse-engineered from
v1.4. **The handshake is unchanged between those versions.**

## Factory baseline contents

Useful as a known-good starting point, since it is a vendor default rather than
one of our edits.

- **32 channels**: 16 digital (`DCH 1`–`DCH 16`) + 16 analog (`ACH 1`–`ACH 16`),
  interleaved in blocks of 8/8/8/8.
- Each frequency appears **twice** — once analog, once digital.
- **Every channel is simplex** (`tx == rx`); no splits, no offsets.
- Analog CTCSS: 67.0, 71.9, 94.8, 136.5 Hz, four channels each, RX tone == TX
  tone. No DCS anywhere in the factory config.
- Byte 33 is `0x80` on all 32 channels → power **high**, TX-admit 0, RX-only
  clear, bandwidth 12.5 kHz. ⚠️ Power bits `&0x03` are `0=high, 2=low` — the
  **inverse** of p64tool's `docs/codeplug-format.md`, confirmed against the CPS
  display. Bandwidth bits `&0x0C>>2` are `0=12.5k, 1=20k, 2=25k`, also
  CPS-confirmed.
- `03` contains ASCII `192.168.10.1`; `05EM01` is named `DigiSys1`; `ML0001`
  holds `HELLO`.

### Frequencies

`461.1125` `461.1375` `461.1625` `468.5625` `468.6125` `468.6625` `456.3375`
`456.4375` `459.6025`/`459.6062` `448.1938` `469.3687` `449.3125` `459.1250`
`444.5500` `457.1750` `442.8750`

All land exactly on the 12.5 kHz raster — a cheap sanity check that a frequency
decode is scaled correctly.

⚠️ **These are vendor defaults, not a licensed channel plan.** They sit in UHF
business/itinerant territory and several fall **inside the 70 cm amateur band**
(442.875, 444.550, 448.1938, 449.3125). Transmitting requires the appropriate
authorization; the factory list is not evidence of one. Do not treat this block
as a legal operating plan.

## The write path

Captured from an OEM CPS write of a modified codeplug, plus a read-after-write
of the same radio:

- `cps/cps_serial_dumps/P4_OEM_FAMILYPLAN_CPS_WRITE_DUMP.txt`
- `cps/cps_serial_dumps/P4_OEM_FAMILYPLAN_CPS_READAFTERWRITE_DUMP.txt`

⚠️ **These two dumps are UTF-16LE with a BOM**; the baseline read dump is UTF-8.
A parser that assumes UTF-8 returns **zero events** rather than an error, which
looks like an empty capture. Git also flags them as `Bin` for this reason. Sniff
the BOM:

```python
raw = open(path, 'rb').read()
text = raw.decode('utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8', 'replace')
```

### Opcode `0x44` = write, ACKs with `0x54`

Every write transaction is answered by a **19-byte reply**:

```
5F 5F 0D 00 00 26 00 23 02 00 54 11 01 00 …
```

So writes follow `0x44` → `0x54`, mirroring the documented read pattern
`0x4D` → `0x55`. p64tool's `PROTOCOL.md` lists `0x44` as the write opcode but
does not document the reply.

### Sequence

```
CONNECT          → 149
op=0x00          → 52
READ  sel=02 00  → 2187      ← one region is READ before any write
WRITE sel=01 00  (276 B)   → 19
WRITE sel=02 00  (2188 B)  → 19
WRITE sel=03 00  (52 B)    → 19
WRITE sel=04 00  (10324 B) → 19
WRITE sel=05 00  (792 B)   → 19
WRITE sel=06 00  (2900 B)  → 19
WRITE sel=07 00  (1108 B)  → 19
WRITE sel=08 00  (18452 B) → 19
WRITE sel=0a 00  (54 B)    → 19
WRITE sel=00 01  (44 B)    → 19
WRITE sel=01 01  (16532 B) → 19
DISCONNECT       → 19
```

### CPS writes 11 regions but reads 13

**`sel=32 00` and `sel=ff ff` are never written.** That is consistent with
`ff ff` being the mostly-erased calibration area — the CPS reads it and leaves it
alone. Useful guard rail for any third-party writer.

### Readback is the written payload plus one leading byte

Diffing every written payload against the corresponding read-after-write payload:

```
readback_payload == b'\x00' + written_payload
```

**Confirmed byte-for-byte on all 11 written regions, no exceptions.** The write
took exactly, and region replies carry a single leading byte ahead of the payload
proper.

🔑 **This independently corroborates the `−15` shift above.** The `.dat` record
header is 16 bytes and the region reply has 1 leading byte, so `.dat` offset 16
lands at region offset 1 — `−15` is `−16 + 1`, not an arbitrary constant. Two
independent captures agree.

### Consequence: `01 01` and `00 01` hold real codeplug content

Both are **written** by the CPS, so they are not padding or scratch space.
`01 01` is 16,531 bytes — the second-largest region — and is not in p64tool's
`REGIONS` table. **A writer that omits these regions produces an incomplete
codeplug.** Worth resolving before using any third-party write path against a
radio you care about.

## Calibration

Per p64tool: `rFF` (~619 B) is ~95 % `0xFF` erased flash on a stock radio and is
*likely* factory/calibration storage, but nothing interpretable is present.
`r32` and `rKL` are all-zero. Consistent with this file — the `KL` records are
zeros.

So **calibration data does not appear to live in the codeplug**, matching the
README's existing note. The write capture supports this independently: the CPS
**never writes** `ff ff` or `32 00`.

## Related

- [`p64tool`](https://github.com/oetiker/p64tool) — **codeplug byte map, protocol, Linux programming tool**
- [`bf888-info`](https://github.com/Chicago-Offline/bf888-info) — BF-888 image format
- [`codeplugger`](https://github.com/Chicago-Offline/codeplugger) — codeplug generator
