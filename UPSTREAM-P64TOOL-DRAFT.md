# Draft: upstream findings for `oetiker/p64tool`

**Status: NOT FILED. Holding for more testing.**

Three findings from OEM CPS serial captures plus a live p64tool read, all against
one radio. Each is written as a self-contained issue body so any of them can be
filed independently once we're confident.

Radio under test:

```
MCU name : DM5
Firmware : 1.0.0.0
Built    : 2025-06-23
Model    : P4 V1.2
```

⚠️ **Single radio, single firmware.** Everything below is `n=1` on hardware
p64tool explicitly flags as outside its validated set
(`WARNING — P4 V1.2/1.0.0.0 not in p64tool's validated set`). That's the main
reason to hold: we cannot currently distinguish "p64tool's docs are incomplete"
from "this firmware behaves differently than the V1.4 CPS it was reverse
engineered against."

Supporting artifacts, all in this repo:

- `cps/cps_serial_dumps/P4_OEM_BASELINE_CPS_READ_DUMP.txt` — CPS read
- `cps/cps_serial_dumps/P4_OEM_FAMILYPLAN_CPS_WRITE_DUMP.txt` — CPS write
- `cps/cps_serial_dumps/P4_OEM_FAMILYPLAN_CPS_READAFTERWRITE_DUMP.txt` — readback
- `p64tool_dumps/p64tool_baseline_factory_20260812/` — live p64tool read

---

## Before filing

- [ ] **Second radio.** Ideally a different firmware, at minimum a second unit.
      All three findings are `n=1`.
- [ ] **Confirm finding 3 is not our cable/driver.** It reproduced on macOS with
      a Prolific PL2303G. Untested on Linux and on a CH340. If it is
      macOS/PL2303G-specific, finding 3 is not an upstream issue at all — it
      belongs in our own notes.
- [ ] **Exercise the write path** on a radio we can afford to recover, to check
      whether the missing regions actually matter in practice. Finding 2's
      severity is currently inferred, not observed.
- [ ] Re-read the current `PROTOCOL.md` and `REGIONS` on upstream `main` and
      confirm these gaps still exist and weren't fixed since our clone.
- [ ] Decide whether to open one combined issue or three. Finding 1 is a clean
      doc patch; finding 2 is a correctness question; finding 3 may be a
      local quirk.

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
