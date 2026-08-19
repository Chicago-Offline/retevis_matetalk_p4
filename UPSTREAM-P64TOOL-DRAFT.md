# Draft: upstream findings for `oetiker/p64tool`

**Status: RE-CHECKED 2026-08-13 against current upstream `main`.**

The "re-read the current `PROTOCOL.md` and `REGIONS` on upstream `main`" item on
the checklist below has now been done, and it changes the picture:

- **Finding 1 (write ACK `0x54`) — still valid, but docs-only.** The write path
  is implemented upstream and does verify the 19-byte `0x54` ACK; `PROTOCOL.md`
  still says "Write (not yet implemented)" and does not document the reply.
- **Finding 2 (missing regions) — STALE, do not file.** Upstream `REGIONS` now
  covers all 13 regions. `00 01` and `01 01` are present as `rKL` and `rML`
  (`rML` = quick-text messages, 32×516 @16), and the 54-byte `op=0x00` frame we
  saw is upstream's MCU-GET (`0x32`) identity probe. Nothing is missing.
- **Finding 3 (0-byte first connect) — still valid and now reproduced on a third
  radio.** See below.
- **NEW, and the important one: `roundtrip` failed on every P4 dump.** Written
  up at the end. Already fixed on branch `feat/p4-roundtrip-fidelity`.
- **NEW 2026-08-13, findings 6 and 7**, from the first OEM CPS export taken of a
  radio we also hold a p64tool dump of. **Finding 6 is fixed** — channel power
  was decoded backwards — though the fix this draft first proposed was wrong,
  which is written up because the mistake generalises. Finding 7, a docs-only
  mislabel of the region-size column, is still open.

Radio under test:

```
MCU name : DM5
Firmware : 1.0.0.0
Built    : 2025-06-23
Model    : P4 V1.2
```

⚠️ The original `n=1` caveat has partly lifted: findings now rest on **four
dumps across three physical radios**, in both factory and CPS-written codeplug
states. Still one firmware (`1.0.0.0`).

Supporting artifacts, all in this repo:

- `cps/cps_serial_dumps/P4_OEM_BASELINE_CPS_READ_DUMP.txt` — CPS read
- `cps/cps_serial_dumps/P4_OEM_FAMILYPLAN_CPS_WRITE_DUMP.txt` — CPS write
- `cps/cps_serial_dumps/P4_OEM_FAMILYPLAN_CPS_READAFTERWRITE_DUMP.txt` — readback
- `p64tool_dumps/p64tool_baseline_factory_20260812/` — live p64tool read
  (🔴 misnamed: this is family state, not factory)
- `p64tool_dumps/p64tool_purple_20260813/` — live p64tool read, genuine factory
  default
- `cps/cps_saves/retevis_matetalkp4_oem_cps_baseline_factory_20260813.dat` — OEM
  CPS export of **that same radio**, three hours later, with the operator's CPS
  screens transcribed alongside. This is what makes findings 6 and 7 possible:
  it is the only place we can see a decoded field and the radio's bytes side by
  side and check that p64tool agrees with the vendor.
- `cps/cps_saves/retevis_matetalkp4_oem_cps_baseline_low682sn_20260813.dat` — the
  same radio again with three deliberate edits (one channel to Low power, DMR ID
  682, real Serial No). The differential that settled finding 6.

---

**Fork status.** Every finding below is implemented on our fork's
`feat/p4-support` / `feat/p4-roundtrip-fidelity` branches, so this is the
evidence base for a PR rather than a list of open questions.

| # | Finding | Kind | Status |
|---|---|---|---|
| 1 | `0x44` write ACKs with `0x54` | doc | valid, docs-only |
| 2 | `REGIONS` omits regions the CPS touches | correctness | **STALE — do not file** |
| 3 | First connect after idle returns 0 bytes | robustness | valid, retry in `proto.rs` |
| 4 | Channel TX power bits documented inverted | field map | fixed (`0272d3e`) |
| 5 | Scan list member array starts at 60, not 58 | field map | fixed (`0272d3e`) |
| 6 | Bandwidth is a 2-bit field read as 1 bit | field map | fixed (`201aab5`) |
| 7 | `roundtrip` not byte-faithful on any P4 dump | correctness | fixed (`feat/p4-roundtrip-fidelity`) |
| 8 | Short region read written to disk with only a warning | robustness | open |
| 9 | Region table `Size` column is frame length | doc | open |

Findings 4–6 are field-map corrections and the strongest of the set: each is
checkable against the CPS UI rather than inferred from a capture.

---

## Before filing

- [x] **Second radio.** Now four dumps across three physical units, in both
      factory and CPS-written codeplug states.
- [ ] **Confirm finding 3 is not our cable/driver.** It reproduced on macOS with
      a Prolific PL2303G. Untested on Linux and on a CH340. If it is
      macOS/PL2303G-specific, finding 3 is not an upstream issue at all — it
      belongs in our own notes.
- [x] **Exercise the write path** on a radio we can afford to recover. Done on
      `p4_02` (yellow), 2026-08-13: identity write, control, and a one-field
      modifying write, then restored byte-for-byte. See
      `p64tool_dumps/p64tool_yellow_20260813/NOTES.md`.
- [x] Re-read the current `PROTOCOL.md` and `REGIONS` on upstream `main`.
      Done — finding 2 is stale, finding 1 is docs-only.
- [x] **Settle finding 6 before filing it.** Done — one channel set to Low in the
      CPS, saved, and diffed against the factory save. It refuted the mask this
      draft proposed and produced the real answer (inverted polarity), which is
      the argument for keeping this checklist item on future findings.


---
- [ ] Confirm the CPS version dependency for findings 4–6. Ours is CPS v1.5;
      p64tool was reverse engineered against v1.4. The offsets came from `.dat`
      payloads, which equal the region bytes, so they apply — but the *labels*
      came from the v1.5 UI.
- [ ] Observe bandwidth value 1 (20 kHz) on hardware. Finding 6's 12.5 and
      25 kHz mappings are confirmed; 20 kHz is inferred from the field being two
      bits wide and has not been round-tripped through the CPS.
- [ ] Decide on one PR versus several issues. Findings 1 and 4–6 are clean
      patches; finding 2 is a question for upstream rather than a defect claim;
      finding 3 may be a local quirk.

---

## Finding 1 — `0x44` write ACKs with `0x54`, undocumented

**Confidence: high.** Observed on all 11 writes in the capture, no exceptions.

`PROTOCOL.md` names `0x44` as the write opcode but does not document the reply.
Every write transaction in the CPS capture is answered with a 19-byte frame:

```
5F 5F 0D 00 00 26 00 23 02 00 54 11 01 00 …
```

So writes follow `0x44` → `0x54`, mirroring the documented read pattern
`0x4D` → `0x55`.

Full observed write sequence:

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

Also worth documenting: diffing every written payload against the corresponding
read-after-write payload gives

```
readback_payload == b'\x00' + written_payload
```

byte-for-byte on all 11 written regions. Region replies carry one leading byte
ahead of the payload proper.

---

---

## Finding 2 — ~~`REGIONS` omits 5 regions the CPS touches~~ STALE, DO NOT FILE

**Re-checked 2026-08-13 against upstream `main`: the gap does not exist.**

Upstream `REGIONS` covers all 13 regions the CPS reads. `00 01` and `01 01` are
there as `rKL` and `rML`, both in the write order too, and `rML` is documented
as the quick-text message table (32 × 516 @16). The 54-byte `op=0x00` preamble
is upstream's MCU-GET (`0x32`) identity probe, also implemented.

Our clone predated that work. The observation below is retained only as a record
of region sizes; **the conclusion drawn from it was wrong.**

The CPS reads 13 regions and writes 11. p64tool's `REGIONS` table covers 9 reads.
Not present in `REGIONS`:

| selector | bytes | CPS reads | CPS writes |
|---|---|---|---|
| `op=0x00` preamble | 52 | yes | — |
| `32 00` | 51 | yes | no |
| `ff ff` | 619 | yes | no |
| `00 01` | 43 | yes | **yes** |
| `01 01` | **16531** | yes | **yes** |

`01 01` is the second-largest region in the codeplug and is written by the CPS,
so it is not padding or scratch space.

**Inference — flagged as inference:** a writer that omits `00 01` and `01 01`
would write an incomplete codeplug. **We have not tested this and have not run
p64tool's write path at all.** It is equally possible those regions are
non-critical, or that p64tool deliberately scopes itself to the settings it
exposes, which its README does claim. Do not file this as a defect claim —
file it as "these regions exist, here are their sizes, is the omission
intentional?"

`ff ff` and `32 00` are read but never written by the CPS, consistent with
`ff ff` being mostly-erased calibration storage. That is a useful guard rail and
matches p64tool's existing note.

---

---

## Finding 3 — first connect after idle returns 0 bytes

**Confidence: raised. Reproduced on a third radio on 2026-08-13**, where it was
strikingly consistent: `info`, `read`, and a verification `read` each failed on
attempt 1 with 0 bytes and succeeded on attempt 2. Still macOS/PL2303G only, so
the cable/driver question below is still open.

The first `CONNECT` after the port has been idle returns 0 bytes. An immediate
retry succeeds, and the link is then stable across many operations.

Observed alternating `info` / `read`, 4 rounds: only round 1 `info` failed, the
other 7 operations succeeded. Also hit once between a successful `info` and the
next `read`.

Suggested upstream change would be a single retry on a 0-byte handshake rather
than failing with `connect handshake failed (got 0 bytes). Radio on? Right
--port?`.

### What we ruled out, and one thing we got wrong

Ruled out by sweep — a 16-combination sweep of baud (115200/57600/38400/9600) ×
modem lines (DTR+RTS / DTR / RTS / neither) returned 0 bytes on **every**
combination, then a subsequent attempt at 115200 DTR+RTS succeeded. So it is not
a baud or line-state problem.

🔴 **Correction worth carrying upstream if we file:** that sweep initially looked
like it proved a CPS-style *double send* was required, because the successful
attempt happened to be the double-send one. Re-running single vs double three
times each showed **single send returns 149 bytes every time**. The sweep's 16
failures were all first-connect-after-idle, not single-vs-double. One
observation looked like a mechanism and wasn't.

The CPS does send `CONNECT` twice ~1 s apart in our capture, which makes the
double-send theory superficially attractive. It is not the explanation — p64tool
waits ~4.0 s on a single write (`149/8 + 4000` ms), so it would still have been
listening for the CPS's second frame.

### Why this might not be upstream's problem

Reproduced only on macOS (Apple silicon) with the in-box Prolific PL2303G at
115200 8N1. Not tested on Linux, not tested with a CH340. p64tool is
Linux-targeted. Plausible this is a PL2303G/DriverKit wake-up behavior rather
than radio or protocol behavior, in which case it belongs in our notes and not
in an upstream issue.

---

---

## Finding 4 — channel TX power bits are documented inverted

**Confidence: high.** Checked against the CPS display for a codeplug written to
the radio and read back.

`docs/codeplug-format.md` documents channel byte 33 as:

> `&0x03` power (0=low, 2=high)

The CPS shows the opposite. In our family/CPD codeplug:

| Channels | byte 33 | `&0x03` | CPS shows |
|---|---|---|---|
| `FAM *` | `0x88` | 0 | **High** |
| `CPD CW1–7` | `0xC2` | 2 | **Low** |

So the mapping is `0=high, 2=low`. Value 1 has not been observed and is presumed
to be the mid/middle setting.

This also changes the reading of a stock codeplug: the factory default is byte 33
`0x80` on all 32 channels, which is **high** power, not low.

A decoder using the documented mapping reports every channel's power backwards,
which is a safety-relevant misread — it understates transmit power on channels a
user may have deliberately set low.

---

---

## Finding 5 — scan list member array starts at 60, not 58

**Confidence: high.** Consistent across three independent `.dat` saves including
a factory-default one, and matches observable CPS behaviour.

`docs/codeplug-format.md` documents scan list records as:

> 56–57 member count (u16 LE); 58–89 member channel numbers (16 × u16 LE)

Offset 58 is not a channel member. It is the **"Current Channel"** entry that the
CPS always displays in a scan list and does not allow you to delete. It is stored
as `0x0000` and **is** included in the count at 56, so real channel members begin
at offset 60.

Observed, member slots read as u16 LE from 58:

```
factory 'Scan 1'  count=1   [0, FFFF, FFFF, ...]
'Family'          count=12  [0, 9, 10, 11, 12, 13, 14, 1, 2, 3, 4, 5, FFFF, ...]
'CPD'             count=8   [0, 6, 7, 8, 15, 16, 17, 18, FFFF, ...]
```

The factory case is the clearest: an empty scan list has `count=1` and a single
`0` entry. Under the documented reading it would be a one-member list containing
channel 0.

Consequences for a decoder following the docs:

- every scan list gains a phantom member "channel 0"
- channel indices are 1-based, so `0` is not a valid channel and the phantom
  entry either renders as garbage or resolves to the wrong channel if the
  decoder treats members as 0-based
- member counts are all reported one too high

Capacity is 15 real members if the record ends at 89, not the documented 16. Our
largest observed list has 11, so we cannot confirm the cap empirically.

---

---

## Finding 6 — channel bandwidth is a 2-bit field read as a single bit

**Confidence: high for 12.5 and 25 kHz, inferred for 20 kHz.** Confirmed against
the CPS display and the stored bytes for the same channels.

`docs/codeplug-format.md` describes channel byte 33 `&0x0C` as
"bandwidth/spacing" without a value table, and the decoder reads a single bit:

```rust
if mode_b == 1 && pb & 0x04 != 0 { 25.0 } else { 12.5 }
```

The field is two bits: `(byte33 & 0x0C) >> 2` → `0 = 12.5, 1 = 20, 2 = 25` kHz.
Value 3 is unobserved.

Our six analog GMRS channels are set to 25 kHz in the CPS and store `0x88`
(bits = 2). Since `0x04` is clear, the old code decoded all of them as 12.5 kHz.

Three consequences:

1. **Reads misreport.** Every 25 kHz channel is reported as 12.5 kHz.
2. **20 kHz is inexpressible.** There is no encoding for value 1, so a config
   cannot represent it and cannot set it.
3. **Narrowing writes silently do nothing.** `apply` did
   `pb &= !0x04; if bw >= 20.0 { pb |= 0x04 }` and never touched `0x08`. Setting
   `bandwidth_khz = 12.5` on one of these channels therefore left the radio at
   25 kHz while the config claimed narrowband. For anyone using p64tool to bring
   a channel into compliance with a narrowband limit, that is a silent failure
   in the unsafe direction.

**`roundtrip` cannot catch this.** We ran it against the affected dump and it
reported `Roundtrip OK: decode->apply is byte-faithful` on all 13 regions —
because `apply` never wrote `0x08`, the bytes were preserved while the decoded
value was wrong. A byte-faithful self-test does not imply a correct decode; it
only proves the bits a decoder ignores are the same bits `apply` leaves alone.
That is worth stating in `DESIGN.md` next to the roundtrip claim.

Evidence:

```
CPS shows 25 kHz  → byte 33 = 0x88  → bits 2
CPS shows 12.5kHz → byte 33 = 0x80  → bits 0
```

The `r08` region of `p64tool_dumps/p64tool_red_familycpd_20260816/` is
byte-identical to the corresponding CPS `.dat` save, so the CPS labels and the
stored bytes describe the same 18 channel records.

---

---

## Finding 7 — `roundtrip` was not byte-faithful on any P4 codeplug — FIXED

**Confidence: high. Reproduced on four dumps, three radios, then fixed and
re-verified.** This is the one that actually mattered.

p64tool's `roundtrip` self-test (decode → re-apply → diff) is the repo's own
stated precondition for trusting the write path. It **failed on every P4 dump in
this repo**: 171 differing bytes, at identical offsets across all three, in
regions `r02`, `r08` and `rML`.

Four independent decode/apply asymmetries, none P4-specific in principle — they
were simply never exercised by the P64 V1.1 sample the field map came from:

1. **Blank-record fill is not a constant** (124 of the 171 bytes). p64tool
   assumed unused `rML` message slots are `0x00`-filled. That holds on a
   factory-fresh radio and is **false on every radio the OEM CPS has written**,
   where they are `0xFF`. On those, decode emitted 32 empty quick-text messages
   and re-apply stamped a record number into 31 slots that should not have been
   touched.
2. **Empty names.** `set_name` wrote a `0x0000` terminator into a name field the
   radio leaves entirely `0xFF`-filled. Programmed-but-unnamed channels are
   common here, so this fired repeatedly.
3. **Channel encryption key slot.** `rec[62]` was zeroed whenever the enable bit
   was clear, discarding the radio's retained last-selected key.
4. **Password sentinel `r02[24]`.** Rewritten unconditionally to `0xF8`, which
   is the factory value; a CPS-written radio holds `0x8F`. Both mean "disabled".

Fixed on branch `feat/p4-roundtrip-fidelity`: preserve an already-blank record
whatever its fill, recognise both fills on decode, keep the stored key slot, and
only rewrite the password byte when the state actually changes. All four dumps
now report `Roundtrip OK`, and the upstream test suite still passes.

**Status 2026-08-13:** fixed and now carried on
`Chicago-Offline/p64tool` branch `feat/p4-support`, together with the connect
retry (finding 3), a short-read guard (finding 5), the `PROTOCOL.md` refresh
(finding 1), and a change that stops p64tool writing `r32`/`rFF`. `roundtrip` is
byte-faithful on all six dumps, and the write path has since been proven on
hardware.

**Filing note:** this is a fix, not a bug report — send the branch as a PR rather
than an issue.

---

---

## Finding 8 — a short region read is written to disk with only a warning

**Confidence: medium. Observed once, mechanism clear.**

One read during the 2026-08-13 session returned `r08` as **5,869 bytes instead
of 18,451** and `rFF` as **1 byte**. p64tool flagged it (`header_ok=NO` in
`manifest.txt`, plus a closing `WARNING:` line) but still wrote the dump
directory and a truncated `codeplug_raw.bin`.

That is a hazard rather than a cosmetic issue: a truncated dump is a valid input
to `--from-dump`, so a short read can silently become the base image for a
write. `read_response` stops on a 250 ms inter-byte gap, so a mid-transfer pause
ends the region early.

Suggested: make a short region a hard error by default, or refuse to load a dump
whose manifest has any `header_ok=NO`.

---

---

## Finding 9 — the region table's `Size` column is frame length, not payload length

**Confidence: high. Docs-only, trivial, but it propagates. Still open on
`feat/p4-support` as of `0272d3e`.**

`docs/codeplug-format.md` says of the region table: *"'Size' is the payload
length `N`"*. The listed values are frame lengths. Measured on all 13 purple
regions:

```
file_size == 18 + payload_len          # 14-byte header + payload + 4-byte trailer
payload_len == u16le(rNN.bin[12..14])  # the header's own length field
```

So `r03` is listed as 51 and its payload is 33; `r08` is listed as 18,451 and its
payload is 18,433. The distinction matters as soon as anything is written to a
region boundary — we hit it decoding a CPS `.dat` record that turned out to
overrun the `r03` payload by two bytes and match anyway, because the frame
trailer begins `FF FF` and is indistinguishable from padding.

Suggested: relabel the column `Frame` and add a `Payload` column, or state the
`18 + N` relationship next to the table.

---

---

## Finding 10 — channel power was decoded backwards — FIXED

> Same defect as **Finding 4** above, which states the corrected mapping. This
> entry is retained because the *route* to it — a wrong first hypothesis,
> refuted by a differential CPS save — is the more useful half.

**Confidence: high. Settled by a differential CPS save, then fixed.** 🔴 **Our
first proposed fix was wrong** — see below, it is the more useful half of this
entry.

`docs/codeplug-format.md` mapped channel record byte 33 as:

> `&0x03` power (0=low, 2=high); `&0x30>>4` TX-admit criteria; `&0x40` RX-only.
> **A** also: `&0x0C` bandwidth/spacing

On the factory-default codeplug byte 33 is `0x80` on all 32 channels, so `&0x03`
is `0` and p64tool reported **Low**. The OEM CPS shows **High** for all 32.

Setting one channel to Low in the CPS and saving moved exactly that byte:

```
08CH09[33]   0x80  ->  0x82        ACH 1, High -> Low
```

**The mask was right; the polarity was inverted.** Bits `[1:0]` are
`0 = high, 2 = low`. Every P4 decode before the fix reported power backwards, and
writing such a config back would have flipped it on the radio. Reads were
unaffected — byte 33 round-trips verbatim — which is why `roundtrip` never
caught it.

Fixed in `Chicago-Offline/p64tool` `feat/p4-support` (`0272d3e`), with the
mapping in `power_from_bits`/`power_to_bits` so decode, apply and the regression
test share one definition. `0x80` is now documented as set on every observed
record, meaning unknown.

### 🔴 What we got wrong, and why it is worth recording

This document originally proposed `(b33 & 0xC0) >> 6`. The argument: `&0x03` is
never set on any channel in any dump, `0x80` always is, and `0x80 >> 6` equals
`2` — the value already documented as "high". A bit that was always set got read
as the field that was always High.

Every step was true and the conclusion was still wrong, because **the sample had
no variation in the thing being measured.** All 32 channels were High, so any
constant in the record could be made to explain the output. That is
curve-fitting to a single point. The tell, in hindsight, was that the hypothesis
required the vendor to have chosen an odd encoding while a simpler one sat right
there.

It cost one CPS edit and a save to find out. **When a hypothesis rests on a
constant, get a second value before writing it down** — and certainly before
filing it upstream, which the checklist happily prevented here.

**Filing note:** fixed, not a report. Goes upstream with the branch.

---

## Related local gotcha — not upstream's problem

On macOS the Prolific PL2303G DriverKit extension must be **enabled** under
System Settings → General → Login Items & Extensions → **Driver Extensions**. A
dext left in `[activated waiting for user]` enumerates a normal-looking
`/dev/cu.PL2303G-USBtoUART*` node, but `TIOCMSET` silently fails, so DTR/RTS
never assert and the radio stays silent — presenting as exactly the same 0-byte
handshake as finding 3.

Check with `systemextensionsctl list`. This cost us an afternoon and produced a
confident but wrong "the cable is broken" conclusion.
