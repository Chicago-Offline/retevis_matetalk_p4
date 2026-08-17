# Draft: upstream findings for `oetiker/p64tool`

**Status: NOT FILED.** All six findings are now implemented on our fork's
`feat/p4-support` branch, so this is no longer a list of open questions — it is
the evidence base for a pull request (or a set of issues, if upstream prefers
them separately).

Six findings from OEM CPS serial captures, OEM CPS `.dat` saves, and live
p64tool reads. Each is written as a self-contained issue body so any of them can
be filed independently.

| # | Finding | Kind | Fixed in fork |
|---|---|---|---|
| 1 | `0x44` write ACKs with `0x54` | doc | `PROTOCOL.md` |
| 2 | `REGIONS` omits 5 regions the CPS touches | correctness | `rKL`/`rML` in `REGIONS` |
| 3 | First connect after idle returns 0 bytes | robustness | handshake retry in `proto.rs` |
| 4 | Channel power bits documented inverted | field map | `0272d3e` |
| 5 | Scan list member 0 is the CPS "Selected" entry | field map | `0272d3e` (`include_selected`) |
| 6 | Bandwidth is a 2-bit field read as 1 bit | field map | `201aab5` |

Findings 4–6 are field-map corrections and are the strongest of the set: each is
checkable against the CPS UI rather than inferred from a capture. Finding 6 is
also the only one with a **silent write-path failure**, and the only one the
existing `roundtrip` self-test provably cannot catch.

Radio under test:

```
MCU name : DM5
Firmware : 1.0.0.0
Built    : 2025-06-23
Model    : P4 V1.2
```

⚠️ **Single radio, single firmware.** Everything below is `n=1`. For findings
1–3 we cannot fully distinguish "p64tool's docs are incomplete" from "this
firmware differs from the V1.4 CPS it was reverse engineered against." Findings
4–6 are less exposed to that doubt because the CPS displays the field and we can
read the stored byte for the same channel.

Supporting artifacts, all in this repo:

- `cps/cps_serial_dumps/P4_OEM_BASELINE_CPS_READ_DUMP.txt` — CPS read
- `cps/cps_serial_dumps/P4_OEM_FAMILYPLAN_CPS_WRITE_DUMP.txt` — CPS write
- `cps/cps_serial_dumps/P4_OEM_FAMILYPLAN_CPS_READAFTERWRITE_DUMP.txt` — readback
- `p64tool_dumps/p64tool_baseline_factory_20260812/` — live p64tool read
- `p64tool_dumps/p64tool_red_familycpd_20260816/` — live read whose `r08` is
  byte-identical to `cps/cps_saves/retevis_matetalk_p4_familywcpd_red.dat`,
  which is what grounds findings 4–6

---

## Before filing

- [ ] **Second radio.** Ideally a different firmware, at minimum a second unit.
      Everything here is `n=1`.
- [ ] **Confirm finding 3 is not our cable/driver.** It reproduced on macOS with
      a Prolific PL2303G. Untested on Linux and on a CH340. If it is
      macOS/PL2303G-specific, finding 3 is not an upstream issue at all — it
      belongs in our own notes.
- [ ] **Exercise the write path** on a radio we can afford to recover, to check
      whether the missing regions actually matter in practice. Finding 2's
      severity is currently inferred, not observed.
- [ ] Re-read the current `PROTOCOL.md` and `REGIONS` on upstream `main` and
      confirm these gaps still exist and weren't fixed since our clone.
- [ ] Confirm the CPS version dependency for findings 4–6. Ours is CPS v1.5;
      p64tool was reverse engineered against v1.4. The offsets came from `.dat`
      payloads, which equal the region bytes, so they apply — but the *labels*
      came from the v1.5 UI.
- [ ] Observe bandwidth value 1 (20 kHz) on hardware. Findings 6's 12.5 and
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

## Finding 2 — `REGIONS` omits 5 regions the CPS touches, 2 of which it writes

**Confidence: high on the observation, unverified on the consequence.**

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

## Finding 3 — first connect after idle returns 0 bytes

**Confidence: LOWEST of the three. Do not file until the checklist above is done.**

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

## Related local gotcha — not upstream's problem

Recording it here so it doesn't get mistaken for a p64tool bug later.

On macOS the Prolific PL2303G DriverKit extension must be **enabled** under
System Settings → General → Login Items & Extensions → **Driver Extensions**. A
dext left in `[activated waiting for user]` enumerates a normal-looking
`/dev/cu.PL2303G-USBtoUART*` node, but `TIOCMSET` silently fails, so DTR/RTS
never assert and the radio stays silent — presenting as exactly the same 0-byte
handshake as finding 3.

Check with `systemextensionsctl list`. This cost us an afternoon and produced a
confident but wrong "the cable is broken" conclusion.
