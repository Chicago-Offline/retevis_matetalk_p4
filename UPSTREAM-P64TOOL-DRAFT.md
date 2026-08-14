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
- [ ] Decide whether to open one combined issue or several.

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

## Finding 4 — `roundtrip` was not byte-faithful on any P4 codeplug — FIXED

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

## Finding 5 — a short region read is written to disk with only a warning

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

## Related local gotcha — not upstream's problem

On macOS the Prolific PL2303G DriverKit extension must be **enabled** under
System Settings → General → Login Items & Extensions → **Driver Extensions**. A
dext left in `[activated waiting for user]` enumerates a normal-looking
`/dev/cu.PL2303G-USBtoUART*` node, but `TIOCMSET` silently fails, so DTR/RTS
never assert and the radio stays silent — presenting as exactly the same 0-byte
handshake as finding 3.

Check with `systemextensionsctl list`. This cost us an afternoon and produced a
confident but wrong "the cable is broken" conclusion.
