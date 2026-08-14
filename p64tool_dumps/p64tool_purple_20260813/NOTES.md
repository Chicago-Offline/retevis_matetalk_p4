# purple — genuine factory-default codeplug

Fourth dump, third physical radio. **This is the first dump in this repo that
actually holds the factory-default codeplug.** The directory named
`../p64tool_baseline_factory_20260812/` does not — see "Corrections" below.

```
MCU name : DM5
Firmware : 1.0.0.0
Built    : 2025-06-23
Model    : P4 V1.2
```

13 regions, `header_ok=yes` on all, 53,381 bytes,
md5 `449156af5f89fa21c89af8799a61ffb1`.

Read on macOS (Apple silicon) via the Prolific PL2303G at 115200 8N1, with
p64tool built from branch `feat/p4-roundtrip-fidelity`. Two independent reads
were byte-identical.

## Contents

32 channels — 16 digital + 16 analog, interleaved in blocks of 8/8/8/8, which is
exactly the layout `../../CODEPLUG.md` describes for the vendor default:

```
DCH 1..DCH 8, ACH 1..ACH 16, DCH 9..DCH 16
```

Serial No `123456789`, DMR ID `1`, 2 zones, 1 contact, 1 scan list, 1 quick-text
message (`HELLO`).

✅ An OEM CPS export of this same radio,
`../../cps/cps_saves/retevis_matetalkp4_oem_cps_baseline_factory_20260813.dat`,
confirms the decode channel by channel — all 32 agree on name, RX, TX, CTCSS,
colour code, contact and RX-group. 62 of its 68 records are byte-identical to
this dump; the 6 that differ are four CPS-authored metadata fields plus the two
normalised bytes below. See `../../CODEPLUG.md` for the full comparison.

## Resolves: `123456789` is the factory-default Serial No

`../p64tool_p4_02_postwrite_selfid439_20260812/NOTES.md` left this open:

> Whether `123456789` is the factory-default Serial No is **still unverified**.
> Neither out-of-box dump shows it … Do not record `123456789` as the default
> without a genuinely untouched radio to check.

This is that radio, and it reads `123456789`. Recorded as the factory default.

The field is at **r01 payload offset 209** (`0xD1`), 32 bytes = 16 UTF-16LE
chars. That is the same field the earlier note called `0xDF` — that figure was
measured from the start of the raw frame file, and `209 + 14 = 0xDF`, so the two
agree. Prefer payload-relative offsets; they are what p64tool's docs use.

## Resolves: the family codeplug is 11 channels, not 12

`../p64tool_cm-p4-02_family_20260812/NOTES.md` flagged an unresolved conflict
between the operator's "6 family channels and 6 digital equivalents" (12) and
`yellow.yml`'s 11 assignments.

Decoding the channel names settles it — **the profile is right, the description
was wrong**. All three family dumps carry the same 11 named channels:

```
digital (5): FAM ALL D, FAM TEAM 1 D, FAM TEAM 2 D, FAM TEAM 3 D, ROAD/TRAVEL D
analog  (6): FAM ALL, FAM TEAM 1, FAM TEAM 2, FAM TEAM 3, ROAD/TRAVEL, FAM RPTR
```

There is no `FAM RPTR D`, matching the profile's own comment that the repeater
channel has no digital counterpart. The `r08` stride is safe to map: records are
72 bytes and channel names decode cleanly as UTF-16LE at record offset 1.

⚠️ The earlier note said `strings` finds nothing readable in `r08`. That was a
tooling artifact — the names are UTF-16LE, which `strings` does not find by
default. Use `strings -el`.

## Corrections to this repo

### 🔴 `p64tool_baseline_factory_20260812/` is misnamed — it is not factory state

Its README entry claims "Factory-fresh, unmodified radio". Its `r08` holds the
**family** codeplug (`FAM ALL D`, `FAM TEAM 1 D`, … `FAM RPTR`), identical in
channel naming to the two dumps explicitly labelled as family.

The same README entry also says the dump matches
`P4_OEM_FAMILYPLAN_CPS_READAFTERWRITE_DUMP.txt` — the *family-plan* readback.
That statement is the correct one; "factory-fresh" contradicts it. The dump is
good data, only the label is wrong.

Consequence: any conclusion in this repo that rested on that dump being a
factory baseline needs re-checking against this one.

## New finding: three bytes distinguish factory state from CPS-written state

Comparing this radio against the three CPS-written dumps, the same split appears
in three independent places:

| item | factory (this dump) | after an OEM CPS write |
|---|---|---|
| `r02` payload[9] (`WW02[24]`, password sentinel) | `0xF8` | `0x8F` |
| `r02` payload[71] | `0x0A` | `0x01` |
| `rML` blank message slots | all `0x00` | all `0xFF` |

The raw CPS baseline capture agrees with the factory column: extracting region
`02` straight out of `P4_OEM_BASELINE_CPS_READ_DUMP.txt` gives payload[9] =
`0xF8`.

### Follow-up: the CPS rewrites two of them on *read*, not on write

This radio was later read by the OEM CPS as well, three hours after the p64tool
read and with no write in between:
`../../cps/cps_saves/retevis_matetalkp4_oem_cps_baseline_factory_20260813.dat`.

p64tool got `f8` / `0a` off the radio. The CPS, reading the same radio the same
evening, put `8f` / `01` in its save file. So the substitution is **the CPS
normalising a codeplug as it ingests it** — the radio was in factory state for
both reads.

That tightens the table above rather than contradicting it. The radio-side split
is downstream of the same behaviour: because the CPS normalises on read, any
codeplug it later writes back carries the normalised bytes, so a CPS-written
radio reads `8f` / `01` from then on. Before, this rested on comparing different
radios; now it is one radio, two readers.

The `rML` fill cannot be checked this way — the `.dat` stores only the populated
message record, never the 31 blank slots — but it fits the same pattern, with
the fill byte chosen by the CPS at write time.

**This resolves both "unexplained" bytes in `../../CODEPLUG.md`.** That document
recorded them as an unresolved `.dat` vs. serial disagreement:

```
020100   .dat 8f …           serial f8 …
020300   .dat 03 01 01 00    serial 03 01 0a 00
```

Both are the same phenomenon: the `.dat` was written by the CPS and carries the
CPS-normalised values, while the serial baseline capture caught the radio in
factory state. They are not two views of one state, so there is nothing
contradictory left to explain. `020100` maps to `r02` payload[9] and `020300` to
payload[69..73], via the documented `−15` shift.

The `rML` fill difference is the same story and has real consequences — see
below.

## Impact on p64tool: the `rML` fill broke the write path

p64tool's `roundtrip` self-test (decode → re-apply → diff, the repo's stated
precondition for trusting a write) **failed on every P4 dump in this repo**: 171
differing bytes, identical offsets across all three.

124 of those 171 were the `rML` fill. p64tool assumed blank message slots are
`0x00`-filled — true for a factory radio like this one, false for every
CPS-written radio, where they are `0xFF`. On those, decode emitted 32 empty
quick-text messages and re-apply then stamped a record number into 31 slots that
should have stayed untouched.

Fixed upstream in `oetiker/p64tool` branch `feat/p4-roundtrip-fidelity`, along
with three smaller asymmetries (empty-name terminator, dropped encryption key
slot, and the `r02[24]` sentinel above). All four dumps now report
`Roundtrip OK`, including this one.

## Second p64tool issue: channel power decodes as Low, the CPS says High

The OEM CPS export of this radio shows **Power = High** on all 32 channels.
Channel byte 33 is `0x80` on all 32, and p64tool's `&0x03` power mask reads `0`
from that — **Low**.

`&0x03` is never set on any channel in any dump in this repo. Reading power as
`(b33 & 0xC0) >> 6` gives `2`, the value p64tool already documents as "high", so
the values look right and the mask looks wrong. Full evidence and the caveat
(every sample is a High-power channel, so it is not yet decisive) in
`../../CODEPLUG.md`.

Reads are unaffected — byte 33 round-trips verbatim either way. Writing power
through p64tool would not.

## Reproducing

```bash
p64tool info --port /dev/cu.PL2303G-USBtoUART10
p64tool read --port /dev/cu.PL2303G-USBtoUART10 --out p64tool_purple_20260813
```

⚠️ **Always check `manifest.txt` before trusting a dump.** One read during this
session returned `r08` as 5,869 bytes instead of 18,451 and `rFF` as 1 byte.
p64tool flagged it (`header_ok=NO`, plus a warning) but still wrote the
directory, so a truncated codeplug is easy to keep by accident. A good read is
53,381 bytes with `header_ok=yes` on all 13 regions.

⚠️ The 0-byte first connect reproduced again, on a third radio: attempt 1 failed,
attempt 2 succeeded, every time. It is consistent enough to just plan on.
