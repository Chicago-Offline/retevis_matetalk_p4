# yellow (p4_02, CO-P4-02) — family-only codeplug, DMR ID 439

Sixth dump. Read immediately after the blue radio, on the same cable, as a
controlled two-radio comparison.

```
MCU name : DM5
Firmware : 1.0.0.0
Built    : 2025-06-23
Model    : P4 V1.2
```

13 regions, `header_ok=yes` on all, 53,381 bytes,
md5 `243d6bd67be5e2d7ec5cfb4f0aa46969`. `roundtrip` OK.

Physically confirmed by the operator as the unit with case serial ending
**1677** = `p4_02` / `CO-P4-02` in `muehlstein-codeplugger-profiles/instances.yml`.

## Contents

- **11 named channels** — the family set only, ham channels stripped:
  5 digital (`FAM ALL D`, `FAM TEAM 1/2/3 D`, `ROAD/TRAVEL D`) and 6 analog
  (`FAM ALL`, `FAM TEAM 1/2/3`, `ROAD/TRAVEL`, `FAM RPTR`).
- **DMR ID `439`**
- r01 Serial No: `50716RP041101677` — the full case serial minus its leading `2`.

Effectively unchanged from `../p64tool_p4_02_postwrite_selfid439_20260812/`:
**4 bytes differ, all in `r01`.** So that dump's state has persisted, and the
"self id 439" configuration is still on the radio.

## 🔑 Settles: the connect-reply string is NOT a per-unit serial

This is the controlled comparison the question needed.

Yellow and blue are unambiguously different radios:

| | yellow (p4_02) | blue (p4_01) |
|---|---|---|
| codeplug md5 | `243d6bd67be5e2d7ec5cfb4f0aa46969` | `15e3d29d9a2c6b2e445e8b8c38702465` |
| DMR ID | 439 | 3207125 |
| named channels | 11 | 19 |
| differing regions | — | r01, r03, r04, r06, r07, r08 |

Both were probed with an identical read-only `CONNECT` and returned a
**byte-identical 149-byte reply**, all 149 bytes, including the digit string
`428734460100152`.

**Conclusion: that string is a model/firmware constant, not a hardware serial.**

⚠️ An earlier version of this claim in `../../CODEPLUG.md` and in the blue notes
asserted the same thing from the three OEM CPS captures. That reasoning was
unsound — it assumed those captures came from different physical radios, which
rested on repo labels this session already proved unreliable. The conclusion
survives; the evidence for it is now a controlled two-radio test instead.

## 🔴 Blue's codeplug carries yellow's serial number

Blue's r01 Serial No reads `101677`. That is **this** radio's case-serial tail.
Blue is `p4_01`, case serial ending **1728**.

The most likely cause is that blue was programmed from a codeplug cloned off
yellow and the Serial No field was never updated. It is a fleet-records issue to
fix in the CPS, not a p64tool defect — but it is a concrete demonstration of why
the r01 serial cannot be trusted as a unit identifier: it silently follows a
cloned codeplug.

## Identifying units from a dump

`instances.yml` records a distinct case serial per radio, and the r01 Serial No
is normally set from its tail:

| instance | tape | case serial | r01 Serial No seen |
|---|---|---|---|
| `p4_01` | blue | `250716RP041101728` | `101677` ⚠️ stale, yellow's |
| `p4_02` | yellow | `250716RP041101677` | `50716RP041101677` ✅ |
| `p4_03` | purple | `250716RP041101784` | `123456789` (factory default, never set) |
| `p4_04` | red | `250716RP041101670` | `101670` ✅ |

So it is a useful *soft* hint, but it is set by hand, it is not always right,
and nothing on the wire corroborates it. Confirm against the case sticker before
recording which unit a dump came from.
