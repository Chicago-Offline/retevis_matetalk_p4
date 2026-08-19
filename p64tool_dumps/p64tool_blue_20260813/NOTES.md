# blue — full `yellow.yml` profile including ham channels

Fifth dump. The blue radio, carrying the complete profile: the family channels
**plus** the ham channels that were stripped from the three
`*_family_*` / `*_baseline_*` dumps.

```
MCU name : DM5
Firmware : 1.0.0.0
Built    : 2025-06-23
Model    : P4 V1.2
```

13 regions, `header_ok=yes` on all, 53,381 bytes,
md5 `15e3d29d9a2c6b2e445e8b8c38702465`. Two independent reads byte-identical.
`p64tool roundtrip` reports OK.

## Verified against the OEM CPS capture

**All 13 regions are byte-identical to
`../../cps/cps_serial_dumps/P4_BLUE_HAM_READ_DUMP.txt`**, the OEM CPS v1.5 read
of this radio.

That is a second independent p64tool-vs-CPS parity check, on a different radio
and a different codeplug from the first one. p64tool and the vendor software pull
the same bytes.

## Contents

32 channel slots, 20 named:

| group | channels |
|---|---|
| Family digital (5) | `FAM ALL D`, `FAM TEAM 1/2/3 D`, `ROAD/TRAVEL D` — 462.575–462.675 |
| Family analog (6) | `FAM ALL`, `FAM TEAM 1/2/3`, `ROAD/TRAVEL`, `FAM RPTR` — 462.550–462.675 |
| Ham analog (4) | `70CM Calling` 446.000, `NS9RC 70` 442.725, `CFMC 70` 443.750, `SARA 70` 444.375 |
| Ham digital (4) | `HS W9CRS`, `HS Parrot`, `HS Local`, `HS Disconnect` — all 430.4375 |

Remaining slots are unprogrammed defaults (400.125 filler, one 442.875).

- **DMR ID `3207125`** — the first dump here with a real registered ID; the
  others hold `682`, `843`, `439`, `1`.
- r01 serial field: `101677`.
- 3 zones, contacts and scan lists populated.

The 11 family channels match `yellow.yml` exactly — 6 analog + 5 digital, no
`FAM RPTR D` — independently confirming the count settled in
`../p64tool_purple_20260813/NOTES.md`.

## 🔴 Correction: neither "serial" identifies a physical radio

This dump's r01 serial field reads `101677`, which is **not this radio's**. Blue
is `p4_01`, case serial ending `1728`; `101677` belongs to `p4_02` (yellow).
Blue was almost certainly programmed from a codeplug cloned off yellow with the
Serial No left unchanged.

Two distinct fields, neither of them a unit id:

1. **r01 payload offset 209** — the "Serial No" shown in the CPS. It is
   *codeplug content*, set by hand and carried along when a codeplug is cloned,
   as this radio demonstrates. `p4_02_postwrite` also shows it being overwritten
   outright.
2. **The CONNECT reply's serial** — `428734460100152`. A controlled test against
   `../p64tool_yellow_20260813/` (a confirmed different radio: different
   codeplug, DMR ID 439 vs 3207125, 11 channels vs 19) returned a
   **byte-identical 149-byte connect reply**. It is a model/firmware constant.

⚠️ An earlier draft of this file reached the same conclusion from the three OEM
CPS captures, on the assumption they came from different physical radios. That
assumption rested on repo labels this session proved unreliable, so the reasoning
was unsound even though the conclusion held. It is now backed by the two-radio
test above.

**Consequence: nothing in this protocol distinguishes one P4 from another.**
Track physical units by case marking or an external record. The r01 serial is a
useful soft hint at best — confirm against the case sticker.

## Factory vs CPS-written state

This radio sits squarely in the CPS-written column of the three marker bytes
identified in `../p64tool_purple_20260813/NOTES.md`:

```
r02[9]  = 0x8F     (factory: 0xF8)
r02[71] = 0x01     (factory: 0x0A)
rML blank slots = 0xFF   (factory: 0x00)
```

Four dumps now sit on the CPS-written side and one (purple) on the factory side,
with no counterexamples.

## ⚠️ Five family channels are digital on GMRS frequencies

`FAM ALL D` and `FAM TEAM 1/2/3 D` and `ROAD/TRAVEL D` are DMR channels on
462.575–462.675 MHz, which is GMRS spectrum. This is deliberate — the profile
calls them "DMR-on-GMRS" — but GMRS is analog-only by rule in the US, so those
channels are not lawful to transmit on there.

Recorded as an observation about the data, not advice. Note that p64tool's
`regs.rs` currently ships only a PMR446 profile, so nothing in the toolchain
flags this; a US/GMRS profile would.
