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

**Record payloads are the same bytes p64tool documents**, at the same
record-relative offsets — a `08CHnn` payload is a 72-byte channel record, so
byte 32 is channel type, 36–39 is RX frequency, and so on per
`docs/codeplug-format.md`. Spot-checked against this file: frequencies at 36/40
decode as plain little-endian Hz, analog sub-tone at 58/60 decodes as CTCSS via
p64tool's `(hi & 0x0F) * 256 + lo` rule, and the bookkeeping u16s at 66–67 and
70–71 match the record keys.

⚠️ Read those as **u16 LE**, per p64tool. Reading the bookkeeping fields as
single bytes happens to work on a 32-channel radio and breaks above 255.

## Factory baseline contents

Useful as a known-good starting point, since it is a vendor default rather than
one of our edits.

- **32 channels**: 16 digital (`DCH 1`–`DCH 16`) + 16 analog (`ACH 1`–`ACH 16`),
  interleaved in blocks of 8/8/8/8.
- Each frequency appears **twice** — once analog, once digital.
- **Every channel is simplex** (`tx == rx`); no splits, no offsets.
- Analog CTCSS: 67.0, 71.9, 94.8, 136.5 Hz, four channels each, RX tone == TX
  tone. No DCS anywhere in the factory config.
- Byte 33 is `0x80` on all 32 channels → power low, TX-admit 0, RX-only clear,
  bandwidth 0.
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

## Calibration

Per p64tool: `rFF` (~619 B) is ~95 % `0xFF` erased flash on a stock radio and is
*likely* factory/calibration storage, but nothing interpretable is present.
`r32` and `rKL` are all-zero. Consistent with this file — the `KL` records are
zeros.

So **calibration data does not appear to live in the codeplug**, matching the
README's existing note.

## Related

- [`p64tool`](https://github.com/oetiker/p64tool) — **codeplug byte map, protocol, Linux programming tool**
- [`bf888-info`](https://github.com/Chicago-Offline/bf888-info) — BF-888 image format
- [`codeplugger`](https://github.com/Chicago-Offline/codeplugger) — codeplug generator
