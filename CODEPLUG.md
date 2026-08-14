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

Two OEM CPS v1.5 reads of a factory-fresh, unmodified radio, 10,818 bytes and
85 lines each:

- `cps/cps_saves/retevis_matetalkp4_oem_cps_baseline_factory_20260812.dat`
- `cps/cps_saves/retevis_matetalkp4_oem_cps_baseline_factory_20260813.dat` —
  read from the **purple** radio, the unit `p64tool_dumps/p64tool_purple_20260813/`
  established as genuinely factory-default.

Plus one deliberate differential:

- `cps/cps_saves/retevis_matetalkp4_oem_cps_baseline_low682sn_20260813.dat` —
  the same radio after three edits and nothing else: `ACH 1` set to **Low**
  power, radio DMR ID set to **682**, and the CPS "Serial No" set to the unit's
  real case serial. Six records differ from the factory save, and because only
  three things changed, most of them bind directly. It settled the power
  question below.

✅ **The two factory saves are byte-identical across all 68 records.** The only
difference in the whole file is `010004`, the save timestamp. This matters
because `p64tool_dumps/p64tool_baseline_factory_20260812/` — the *p64tool* dump
with a similar name — turned out to be mislabelled family state, which cast
doubt on everything else dated 0812. The `.dat` survives that re-check: its
"factory-fresh" label is correct.

It also means the factory codeplug is reproducible unit-to-unit. Serial No
`123456789` and DMR ID `1` are vendor defaults, not per-unit values, so a
factory read of any P4 should produce this same content.

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

Verified twice. The stronger check is **same radio, same day, two readers**: the
0813 `.dat` (OEM CPS) against `p64tool_dumps/p64tool_purple_20260813/` (p64tool
serial read). All 68 records are comparable because that dump has every region,
and **62 of 68 match byte-for-byte**.

| Key prefix | Region | Records matching |
|---|---|---|
| `01` | `r01` | 6/10 |
| `02` | `r02` | 8/10 |
| `03` | `r03` | 1/1 ✅ |
| `04` | `r04` | 2/2 ✅ |
| `05` | `r05` | 2/2 ✅ |
| `06` | `r06` | 1/1 ✅ |
| `07` | `r07` | 2/2 ✅ |
| `08` | `r08` | **32/32 ✅** |
| `0A` | `r0A` | 1/1 ✅ |
| `KL` | `rKL` | 6/6 ✅ |
| `ML` | `rML` | 1/1 ✅ |

The earlier check — the 0812 `.dat` against
`cps/cps_serial_dumps/P4_OEM_BASELINE_CPS_READ_DUMP.txt`, a *different* radio —
gave 54/61 and is superseded. Every one of the 6 remaining mismatches is
accounted for below; none is an unexplained decode failure.

So a `08CHnn` payload *is* a 72-byte channel record and p64tool's field offsets
apply within it — byte 32 channel type, 36–39 RX frequency, and so on per
`docs/codeplug-format.md`.

⚠️ **To compare a `.dat` record against a p64tool `rNN.bin` file, the shift is
`-1`, not `-15`.** Both are true and it is easy to lose an afternoon here:

```
rNN.bin       = 14-byte frame header ++ payload ++ 4-byte trailer (FF FF 55 AA)
payload_offset = dat_offset - 15
file_offset    = dat_offset -  1        # what you index in rNN.bin
```

p64tool stores the **full frame**, not the payload. Using `-15` against the file
reproduces the classic symptom — every region mismatching from its very first
byte — which reads like a broken shift and is really a 14-byte header.

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

**2. Two single-byte differences — the CPS normalises them on read.**

```
020100   .dat 8f …           radio f8 …
020300   .dat 03 01 01 00    radio 03 01 0a 00
```

Via the `-15` shift, `020100` is `r02` payload[9] (`WW02[24]`, the password
sentinel — both values mean "disabled") and `020300` is payload[69..73], whose
differing byte is payload[71].

🔑 **The 0813 save pins the mechanism down, because it is the same radio.**
purple was read by p64tool at 19:21 and by the OEM CPS at 22:43 on 2026-08-13,
with no write in between. p64tool read `f8` / `0a`; the CPS wrote `8f` / `01`
into its `.dat`. Nothing about the radio changed, so **the substitution happens
inside the CPS when it ingests a codeplug**, not on the radio.

That is a correction of emphasis, not of fact. The earlier reading — "the `.dat`
carries CPS-normalised values, the serial capture caught factory state" — was
right, but it was an inference from two different radios. It is now directly
observed, and it explains the radio-side split as a consequence: because the
CPS normalises on read, whatever it later writes back carries the normalised
values, so any radio it has written reads `8f` / `01` from then on.

| dump | `r02` payload[9] | payload[71] |
|---|---|---|
| `p64tool_purple_20260813` (factory) | `0xf8` | `0x0a` |
| all five other dumps (CPS-written) | `0x8f` | `0x01` |

A third item splits the same way: **`rML` blank message slots are `0x00` on a
factory radio and `0xFF` after a CPS write** — confirmed on the same six dumps,
15,996 fill bytes each. That one broke p64tool's write path — see
`p64tool_dumps/p64tool_purple_20260813/NOTES.md`.

Note the `.dat` cannot show the `rML` fill: it stores only the one populated
message record (`ML0001`), never the 31 blank slots. The fill byte is chosen by
the CPS at write time, which is consistent with the same normalise-on-ingest
behaviour.

**3. Region `03` length mismatch — explained: the record overruns the payload.**
`030000` is 34 bytes in the `.dat`, and the `r03` **payload is 33 bytes**. Since
the record starts at payload offset 1, its last two bytes land past the payload
end, in the frame trailer:

```
r03.bin   51 bytes = 14 header + 33 payload + 4 trailer (ff ff 55 aa)
030000    occupies file bytes 15..48 — payload[1..32] plus trailer[0..1]
```

It compares clean only because the trailer begins `ff ff`, indistinguishable
from the `0xFF` padding the record would otherwise carry. The CPS evidently
emits a fixed-size record here rather than a payload-bounded one. Harmless for
reading; **a writer that echoes 34 bytes back into a 33-byte region is not.**

⚠️ The 33 comes from the frame header, not from p64tool's docs. Its region table
labels the `Size` column "the payload length `N`", but the values listed are
**frame** lengths — `r03` is 51 there. Across all 13 purple regions,
`file_size == 18 + payload_len`, with `payload_len` read from `rNN.bin[12..14]`
as u16 LE. Trust the header field.

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
settings it *exposes*, and these may be deliberately ignored. ~~But **`01 01` is
16,531 bytes and nothing is known about its contents.**~~ **Stale:** current
upstream `main` reads all 13 regions, including `00 01` and `01 01`, and the
54-byte `op=0x00` frame is its MCU-GET (`0x32`) identity probe. `01 01` is the
quick-text message table.

## Protocol confirmation

The same capture confirms p64tool's `PROTOCOL.md` is accurate for this radio:

- Connect frame is **byte-identical** to p64tool's, all 38 bytes:
  `5F5F 1E00 0023 0026 0200 4011 1200` + 20 × `00` + `FFFF55AA`
- Reply is 149 bytes, prefix `5F5F 8F00 0026 0023 0200 5011`, exactly as
  documented
- UTF-16LE fields in the reply decode as firmware `V1.0.0.0` and serial
  `428734460100152`

🔴 **That value is NOT a per-unit serial — it is a model/firmware constant.**
Verified by a controlled test: two radios confirmed distinct (`p4_01` and
`p4_02` — different codeplugs, DMR IDs 3207125 vs 439, 19 vs 11 channels,
physically swapped between reads) returned **byte-identical 149-byte connect
replies**. The r01 "Serial No" is no better as a unit id: it is codeplug content
set by hand, and one radio in the set carries a neighbour's value because its
codeplug was cloned. **Nothing in this protocol distinguishes one P4 from
another.** See `p64tool_dumps/p64tool_yellow_20260813/NOTES.md`.

The capture was taken with **CPS v1.5**; p64tool was reverse-engineered from
v1.4. **The handshake is unchanged between those versions.**

## Factory baseline contents

Useful as a known-good starting point, since it is a vendor default rather than
one of our edits.

✅ **Decoded from the bytes and cross-checked against the operator's CPS screens,
channel by channel: all 32 agree** — name, RX, TX, CTCSS, colour code, contact,
RX-group and scan-list assignment. The field map below is therefore confirmed
end-to-end on this codeplug, not just plausible.

- **32 channels**: 16 digital (`DCH 1`–`DCH 16`) + 16 analog (`ACH 1`–`ACH 16`),
  interleaved in blocks of 8/8/8/8 — records 1–8 `DCH 1`–`8`, 9–24 `ACH 1`–`16`,
  25–32 `DCH 9`–`16`.
- **Every channel is simplex** (`tx == rx`); no splits, no offsets.
- Each frequency appears **twice**, once analog and once digital — except pair 9,
  where analog is `459.602500` and digital is `459.606250`, 3.75 kHz apart. It
  is the one asymmetry in the table and it is in the vendor default, not a typo
  in transcription: both the `.dat` and the p64tool dump carry it.
- Analog CTCSS: 67.0, 71.9, 94.8, 136.5 Hz, four channels each, RX tone == TX
  tone. No DCS anywhere in the factory config.
- All digital channels: colour code 1, TS1, TX contact `Group 1`, RX group
  `GroupList 1`.
- No channel is assigned a scan list (index 0), and none is RX-only.
- TOT byte 44 is `0x24` (36) on all 32.
- `03` contains ASCII `192.168.10.1`; `05EM01` is named `DigiSys1`; `ML0001`
  holds `HELLO` (record 1, length 5).

### Channel power was decoded backwards — RESOLVED, and our first fix was wrong

p64tool's `docs/codeplug-format.md` mapped channel byte 33 as `&0x03` power,
`0=low, 2=high`. On the factory codeplug byte 33 is `0x80` on every channel, so
`&0x03` reads `0` → **Low**, while the OEM CPS displays **High** on all 32.

The differential save settles it. Setting `ACH 1` to Low in the CPS moved that
one byte and nothing else in the record:

```
08CH09[33]   0x80  ->  0x82        ACH 1, High -> Low
```

So the **mask was right and the polarity was inverted**: bits `[1:0]` are
`0 = high, 2 = low`. Every P4 decode before this reported power backwards, and
writing such a config back would have flipped it on the radio. Fixed upstream in
`Chicago-Offline/p64tool` `feat/p4-support` (`0272d3e`), with the mapping moved
into `power_from_bits`/`power_to_bits` so decode, apply and the regression test
share one definition.

🔴 **The fix this document proposed first — `(b33 & 0xC0) >> 6` — was wrong.**
Worth keeping, because the reasoning felt tight and wasn't. The argument was:
`&0x03` is never set on any channel in any dump, `0x80` always is, and
`0x80 >> 6` happens to equal `2`, the value already documented as "high". So a
bit that was always set got read as the field that was always High.

Every step was true and the conclusion was still wrong, because **the sample had
no variation in the thing being measured** — all 32 channels were High. With one
value of the output, any constant in the record can be made to explain it. That
is curve-fitting to a single point, and the giveaway was that the hypothesis
needed the vendor to have picked an odd encoding when a simpler one was sitting
there.

Cost of testing it: one CPS edit and a save. **When a hypothesis rests on a
constant, go get a second value before writing it down.**

`0x80` remains unexplained — set on every channel record observed, in every dump
and every state. Upstream now records it as unknown rather than folding it into
the power field, which is the right place for it.

The other byte-33 fields do check out against the CPS: `&0x40` RX-only is clear
and the CPS shows RX Only = No; blue's `0x88` channels carry `0x08` in the
documented analog `&0x0C` bandwidth field.

### Zones, scan list, messages

- **2 zones**, both full: `Zone 1` = the 16 digital channels (records 1–8 and
  25–32), `Zone 2` = the 16 analog channels (records 9–24). Member count at
  record offset 34–35 reads 16 for both; members are 1-based channel record
  numbers, u16 LE, from offset 36.
- **1 scan list**, `Scan 1`, member count 1 — and the single member is
  `0x0000`.

  🔑 **That `0` is the "Selected" entry the CPS shows, and it is a sentinel, not
  a placeholder or an empty slot.** Real channel references are 1-based
  everywhere else in the codeplug — the zone member lists above run `0x0001` to
  `0x0020` — so `0` cannot denote a channel. It is the reserved id for "whatever
  channel is currently selected", and the member count of 1 confirms the slot is
  genuinely occupied rather than blank (blank members are `0xFFFF`).

  Now handled upstream as `[[scan]] include_selected`. It mattered more than it
  looked: `decode` had been dropping the member and `apply` unconditionally
  re-adding it, so a scan list *without* "Selected" could not be represented and
  would have been corrupted on write.

  The rest of `Scan 1` is unset: designated/revert TX channel `0xFFFF`, priority
  channel 1 `0xFFFF`, priority channel 2 `0xFFFF`, all 15 remaining member slots
  `0xFFFF`.
- **1 quick-text message**, `HELLO`. The other 31 `rML` slots are blank.

## What else the differential save moved

Six records differ between the factory save and `..._low682sn_20260813.dat`.
Three were the requested edits, one is bookkeeping, and two were not asked for.

**Requested — all three bind cleanly:**

| Record | Change | Field |
|---|---|---|
| `08CH09[33]` | `0x80` → `0x82` | `ACH 1` power, High → Low |
| `030000[0..1]` | `01 00` → `82 06` | radio DMR ID, 1 → 682 |
| `010009` | `123456789` → 16 chars | CPS "Serial No" |

The DMR ID confirms the **BCD little-endian** encoding p64tool documents:
`82 06` reads as digit pairs `82` then `06`, least-significant byte first, giving
`682`. Not a u16 — `0x0682` would be 1666.

⚠️ **The Serial No field is full at 16 characters, so it has no NUL
terminator** and runs straight into the field at payload 241. Read it
length-bounded, not NUL-bounded; the factory value `123456789` is short enough to
terminate and hides the problem. It is codeplug data and travels with a clone,
so it is still not a hardware id — see
`p64tool_dumps/p64tool_yellow_20260813/NOTES.md`.

**Bookkeeping:** `010004`, the save timestamp.

**Not requested, and worth watching:** the CPS rewrote nine bytes around the
password area that the operator never touched.

```
r02 payload[28..36]   factory  00 00 00 00 00 00 00 00 00
                      after    ff ff ff ff ff ff ff ff 00
```

That is `020100[19]` plus the first seven bytes of `02CODE` — the record whose
key literally reads `CODE`, and which p64tool leaves unbound. No password was
set in either state (`WW02[24]` is the sentinel, and neither `0xF8` nor `0x8F`
equals the "enabled" value `2`), so both presumably mean "no code". This is the
same shape as the `8f`/`f8` and `rML`-fill normalisations: two encodings of an
empty field, one factory and one CPS-authored.

**It is not a decode problem — it is a write-path caution.** p64tool preserves
these bytes verbatim, which is the correct behaviour for bytes nobody has bound.
Flagged only so that a future differential does not mistake a CPS artifact for
an operator edit.

### Frequencies

`461.1125` `461.1375` `461.1625` `468.5625` `468.6125` `468.6625` `456.3375`
`456.4375` `459.6025`/`459.60625` `448.19375` `469.36875` `449.3125` `459.1250`
`444.5500` `457.1750` `442.8750`

🔴 **They do NOT all land on the 12.5 kHz raster.** An earlier revision of this
document said they did and offered it as "a cheap sanity check that a frequency
decode is scaled correctly". It is the opposite: a decoder validated that way
would reject its own correct output. Four of the seventeen are off it:

| frequency | 12.5 kHz | 6.25 kHz |
|---|---|---|
| `448.193750` | no | yes |
| `469.368750` | no | yes |
| `459.606250` | no | yes |
| `459.602500` | no | **no** — 2.5 kHz raster |

`459.6025` sits on neither grid. Whatever check you use, it has to accept that
one. Frequencies are plain u32 LE Hz at channel offsets 36–39 and 40–43, so
there is nothing to scale and no raster assumption is needed.

⚠️ **These are vendor defaults, not a licensed channel plan.** They sit in UHF
business/itinerant territory and several fall **inside the 70 cm amateur band**
(442.875, 444.550, 448.19375, 449.3125). Transmitting requires the appropriate
authorization; the factory list is not evidence of one. Do not treat this block
as a legal operating plan.

### Tones — settings recorded, bytes not yet bound

The operator's CPS screens for the factory codeplug read: **Disable All Tones**
off, **Talk Permit Tone** = *Analogue & Digital*, and all fourteen tone options
enabled (Warning, Channel Busy Lock, TOT, TOT Pre Alarm, Battery Low, Empty
Channel, Power On, Call Alert, Radio Kill, Radio Active, Private Call, Group
Call, All Call, Empty Contacts).

The corresponding bytes, for whoever binds them next:

```
020400  = ec 00 0c ff        →  WW02[100..103], r02 payload[85..88]
0A0000  = 05 00 01 03 03 0a 01 01 01 01 01 01 01 00 01 01 01
          01 01 00 01 00 01 00 01 00 01 01 01 01 01 01 01
```

p64tool documents `WW02[100]`/`[101]` as talk-permit-tone and all-tones-off,
with `WW02[100] == 0xCD` muting everything. That is **consistent** here:
`WW02[100]` is `0xEC`, not `0xCD`, and tones are on.

⚠️ **Beyond that, do not guess.** Two decodes that look inviting are both wrong:
the fourteen toggles are not a bitfield in `WW02[100..101]` (all fourteen are
enabled, and neither `0xEC 0x00` nor its complement has fourteen matching bits),
and they are not a fourteen-byte run of `01` in `r0A` either (the longest run
there is seven, broken by `00` at record offsets 13, 19, 21, 23 and 25).

The comparison that would settle it is available: `retevis_matetalk_p4_family.dat`
differs from the factory save at exactly these bytes — `020400` reads `28 08 0c ff`
there, so `WW02[100]` = `0x28` and `[101]` = `0x08`. Capture that radio's Tones
screen and the two saves become a differential pair.

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
