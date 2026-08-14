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

This dump's r01 serial field reads `101677`, the same value as
`../p64tool_cm-p4-02_family_20260812/`. **That does not make them the same
radio**, and an earlier reading of this session that inferred so was wrong.

Two distinct fields, neither of them a unit ID:

1. **r01 payload offset 209** — the "Serial No" shown in the CPS. It is
   *codeplug content*: it is written by the CPS and travels with the codeplug,
   so two radios flashed from the same source share it. Also confirmed by
   `p4_02_postwrite`, where it was simply overwritten with a different string.
2. **The CONNECT reply's serial** — `428734460100152`. Decoding it from all
   three CPS captures in this repo, spanning at least two physical radios, gives
   **the same value every time**. It is constant, not per-unit.

`../../CODEPLUG.md` describes the connect-reply value as "serial
`428734460100152`", which reads as a unit serial. It is not one — it is the same
on every radio observed.

**Consequence: nothing in this protocol distinguishes one P4 from another.**
Track physical units by case marking or by an external record, never by either
of these fields. Any past conclusion of the form "same serial, therefore same
radio" needs re-checking.

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
