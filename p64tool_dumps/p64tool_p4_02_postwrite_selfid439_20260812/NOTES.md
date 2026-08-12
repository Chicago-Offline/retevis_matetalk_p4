# p4_02 (CO-P4-02, yellow) — post-CPS-write, self-id 439

Third dump of the session. Same physical radio as
`../p64tool_cm-p4-02_family_20260812/`, read ~25 min later, after a CPS write
that was intended to install the family codeplug and set the radio's Serial No.

```
MCU name : DM5
Firmware : 1.0.0.0
Built    : 2025-06-23
Model    : P4 V1.2
```

13 regions, `header_ok=yes` on all, 53,381 bytes,
md5 `32b6068900a22925e889d42cb1df346b`.

Operator description of the write: "installed the family channel codeplug on the
yellow radio with self id 439 and the full serial number minus the leading 2".

## Result: the write PARTIALLY applied

### ✅ Serial No field took the edit

`r01` `0xDF`, UTF-16LE:

| dump | value |
|---|---|
| **this dump** | `50716RP041101677` |
| p4_02 earlier today | `101677` |
| p4_04 (out-of-box) | `101670` |

`instances.yml` gives `p4_02.case_serial: 250716RP041101677`. The written value
is that serial minus the leading `2`, exactly as described. **This write landed.**

### 🔴 Channel data did NOT — `r08` reverted to factory state

`r08` in this dump is **byte-identical to the out-of-box `p4_04` dump**: 0 of
18,451 bytes differ.

Unprogrammed-row count (signature `0700c08000f0000000`, all on 72-byte
boundaries):

| dump | default rows |
|---|---|
| p4_04 (out-of-box) | 13 |
| p4_02 earlier today | 4 |
| **this dump** | **13** |

The radio went 4 → 13. The family channels that were present on this unit at
16:31 are **gone**, and channel state matches a factory radio.

⚠️ **Cause not established.** A plausible reading is that the CPS session started
from a blank/default codeplug rather than loading the family one first, so it
pushed defaults over the existing channels — but that is inference from the byte
state, not something observed in the CPS. Needs confirmation on the radio's own
menu (are the FAM channels still listed?) before it is treated as fact.

This dump is retained as the evidence of that state.

## 🔴 Corrects an earlier claim in this repo's history: serial field width

Earlier in the session I stated the Serial No field was "6 digits". **Wrong.**

The field is **fixed-width, 32 bytes = 16 UTF-16LE chars**, spanning
`0xDF`–`0xFE`. The neighbouring `v1.01` field sits at `0xFF` in all three dumps
and does not move.

`101677` and `101670` were merely *short values* occupying that field. Two
samples that both happened to be 6 digits made a wrong inference look
well-supported. The 16-char value written here fills the field exactly, which is
what exposed the error.

⚠️ Also note this dump has **no NUL terminator** after the serial — the value
runs the full 16 chars. A naive reader that scans for a NUL will run straight
into the adjacent `v1.01` field and return `50716RP041101677v1.01`. Read the
field by its fixed width, not by terminator.

## Open

- Whether `123456789` is the factory-default Serial No is **still unverified**.
  Neither out-of-box dump shows it: `p4_04` already carried `101670`, the tail of
  its own case serial. Do not record `123456789` as the default without a
  genuinely untouched radio to check.
