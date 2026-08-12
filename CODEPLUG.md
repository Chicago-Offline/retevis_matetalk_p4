# P4 CPS `.dat` codeplug format

Decoded from `cps/cps_saves/retevis_matetalkp4_oem_cps_baseline_factory_20260812.dat`
— an OEM CPS v1.5 read of a **factory-fresh, unmodified** radio. That provenance
is what makes it useful: every value below is a vendor default, not one of our
edits.

## 🔴 It is not a binary image

Unlike the BF-888 `.img` (see [`bf888-info`](https://github.com/Chicago-Offline/bf888-info)),
this is **ASCII text with CRLF line endings**, 10,818 bytes, 85 lines. Hex bytes
are written as space-separated ASCII pairs. Any tooling that assumes a binary
blob will fail immediately.

```
Model=P4 V1.5
010001 00016=50 00 34 00 20 00 56 00 31 00 2E 00 32 00 00 00 FF FF ...
```

### Line grammar

```
<6-char record key> <5-digit offset>=<hex bytes, space separated, trailing space>
```

⚠️ **The record key is 6 characters and may contain letters *and spaces*** —
`010001`, `02CODE`, `02 KEY`, `08CH01`, `KL0001`. A regex like `^([A-Z]+)(\d+)`
matches only a fraction of the file and silently drops the rest. Anchoring on
**exactly 6 characters** parses 68/68 records with zero failures.

⚠️ **The 5-digit field is a byte OFFSET, not a length.** I initially read it as a
length and got a 25-of-25 "mismatch," which is the tell that the assumption was
wrong rather than the file. Within a prefix the offsets advance by the previous
record's byte count — for the channel block, exactly 72 each time.

Blank lines separate sections and carry no data.

## Record prefixes

| Prefix | Records | Contents |
|---|---|---|
| `01` | 10 | Model/firmware identity strings, build dates, CPS version |
| `02` | 10 | Radio-wide settings, incl. `02CODE` and `02 KEY` |
| `03` | 1 | Network config — contains ASCII `192.168.10.1` |
| `04` | 2 | `04E401` group, `04E501` group list |
| `05` | 2 | `05EM01` — ASCII `DigiSys1` |
| `06` | 1 | 90 bytes, undecoded |
| `07` | 2 | 68 bytes each, undecoded |
| `08` | **32** | **Channel records — 72 bytes each** |
| `0A` | 1 | 33 bytes, undecoded |
| `KL` | 6 | 4 bytes each, uniform stride |
| `ML` | 1 | 14 bytes, ASCII `HELLO` in UTF-16LE |

## Channel record (`08CHnn`, 72 bytes)

Factory default is **32 channels**: 16 digital (`DCH 1`–`DCH 16`) and 16 analog
(`ACH 1`–`ACH 16`), interleaved in blocks.

| Offset | Width | Field | Notes |
|---|---|---|---|
| `0x00`–`0x1F` | 32 | Channel name | **UTF-16LE**, `00 00` terminated, `FF` padded |
| `0x20` | 1 | Mode-ish flag | `0x00` analog / `0x01` digital (see caveat) |
| `0x22` | 1 | Paired flag | `0x7D` analog / `0xFF` digital |
| `0x24`–`0x27` | 4 | **RX frequency** | uint32 **little-endian, plain Hz** |
| `0x28`–`0x2B` | 4 | **TX frequency** | uint32 little-endian, plain Hz |
| `0x30` | 1 | Digital flag | `0x01` DCH / `0x00` ACH |
| `0x3A`–`0x3B` | 2 | **CTCSS RX** | uint16, **tenths of Hz** (analog only) |
| `0x3C`–`0x3D` | 2 | **CTCSS TX** | uint16, tenths of Hz (analog only) |
| `0x42` | 1 | Index **within** its DCH/ACH block | 1–16, resets per block |
| `0x46` | 1 | **Absolute channel slot** | 1–32, matches the `08CHnn` key index |

### Frequencies are plain little-endian Hz

No BCD, no scaling factor — the opposite of the BF-888.

```python
rx = struct.unpack_from("<I", rec, 0x24)[0]   # 461112500 -> 461.1125 MHz
```

All 32 land exactly on the 12.5 kHz raster (integer multiples, verified), which
is the cheap sanity check that the scaling is right.

### CTCSS is tenths of a Hz

`0x3A` = `670` → **67.0 Hz**. Factory tones across the analog block: 67.0 (×4),
71.9 (×4), 94.8 (×4), 136.5 (×4). RX and TX tone are identical on every channel.

Digital channels hold `00 C0 80 00` in `0x3A`–`0x3D`, which is **not a tone** —
it's whatever the digital path uses that region for. Undecoded.

### Every factory channel is simplex

`tx == rx` on all 32. Same finding as the BF-888: no split, no offset, no
TX-inhibit in the factory config.

### Analog vs digital differ in a fixed byte set

Two exact signatures, 16 channels each, no variation within a group:

```
DCH:  0x30=01  0x37=FD  0x39=07  0x3E=F0
ACH:  0x30=00  0x37=40  0x39=00  0x3E=00
```

⚠️ **Do not read these as four independent booleans.** They are perfectly
correlated across a 32-channel sample, so this file **cannot** distinguish "the
mode flag" from "settings that happen to co-vary with mode." Separating them
needs a config where one is changed alone.

## Frequencies in the factory config

`461.1125` `461.1375` `461.1625` `468.5625` `468.6125` `468.6625` `456.3375`
`456.4375` `459.6025`/`459.6062` `448.1938` `469.3687` `449.3125` `459.1250`
`444.5500` `457.1750` `442.8750`

Each appears **twice** — once analog, once digital.

⚠️ **These are vendor defaults, not a licensed channel plan.** They sit in UHF
business/itinerant territory, and several are **inside the 70 cm amateur band**
(442.875, 444.550, 448.1938, 449.3125). Transmitting on them requires the
appropriate authorization; the factory list is not evidence of one. Do not treat
this block as a legal operating plan.

## Not decoded

Honest gaps rather than guesses:

- `0x2C` — `36` on all 32 channels, and `0x2D` differs (`00` vs `05`) between
  analog and digital. Purpose unknown.
- `0x31`–`0x39` beyond the mode signature: power level, bandwidth, squelch,
  scan, and busy-lock all live somewhere in here and are **not individually
  resolved**. A factory read cannot separate them — every DCH is identical and
  every ACH is identical.
- Prefixes `06`, `07`, `0A`, `KL`, and the `02` block internals.
- `03` holds `192.168.10.1`; the surrounding structure is unexamined.

**To resolve the rest, the productive move is differential reads:** change one
setting in the CPS, save, diff. One-byte-at-a-time beats staring at a single
file.

## Related

- [`bf888-info`](https://github.com/Chicago-Offline/bf888-info) — BF-888 image format
- [`p64tool`](https://github.com/oetiker/p64tool) — upstream P4/P64 codeplug work
- [`codeplugger`](https://github.com/Chicago-Offline/codeplugger) — codeplug generator
