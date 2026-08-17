# Red radio — family + CPD codeplug

Live read of the red unit carrying the family channels plus the seven RX-only
CPD channels, taken after the codeplug was written from the OEM CPS.

```
MCU name : DM5
Firmware : 1.0.0.0
Built    : 2025-06-23
Model    : P4 V1.2
Gate     : OK (known P64 layout)
```

13 regions, `header_ok=yes` on all, 53,381 bytes,
md5 `11f9d9dde528999a5762ac6dc3107469`.

The first handshake returned 0 bytes and p64tool's retry recovered it on attempt
2 of 5 — the same first-connect-after-idle behaviour recorded as finding 3 in
`../../UPSTREAM-P64TOOL-DRAFT.md`, now handled automatically rather than fatal.

## This dump is tied to a CPS `.dat`

`r08` is **byte-identical** to the 18 channel records in
`../../cps/cps_saves/retevis_matetalk_p4_familywcpd_red.dat`, and `r04`'s
contacts and RX-group list match it too. The radio holds exactly what the CPS
saved.

That pairing is what makes this dump useful: the CPS shows a *label* for a field
and the dump shows the *byte* for the same channel, so field-map claims can be
checked in both directions. It is the evidence base for findings 4–6 upstream
(power bits, scan-list "Selected" member, bandwidth as a 2-bit field).

⚠️ Read region files as **frames**, not payloads. `rNN.bin` is the full frame:
14-byte header, payload, 4-byte trailer. The `−15` `.dat`-offset relationship in
`../../CODEPLUG.md` applies to the payload, so a channel record for `.dat` offset
`o` lives at `frame[o - 1]`. Indexing the frame directly with `−15` yields zero
matching records with almost every byte different — which reads like the radio
disagrees with the save when in fact the parser is misaligned.

## Diff vs `../p64tool_baseline_factory_20260812/`

| region | bytes differing | of |
|---|---|---|
| `r01` | 29 | 275 |
| `r06` | 36 | 2899 |
| `r07` | 27 | 1107 |
| `r08` | 293 | 18451 |

Byte-identical: `r02`, `r03`, `r04`, `r05`, `r0A`, `r32`, `rFF`, `rKL`, **`rML`**.

`r06`/`r07` differ because this codeplug has two scan lists and two zones where
the other has one of each; `r08` differs by the seven added CPD channels.

### `rML` is unchanged for the third time

The 16,531-byte undocumented region (`sel 01 01`) is again byte-identical, now
across three dumps spanning two physical units and three different channel
layouts. Adding channels, zones and scan lists does not touch it. Consistent with
the negative result in `../p64tool_cm-p4-02_family_20260812/NOTES.md`.

## 🔴 `p64tool_baseline_factory_20260812/` is misnamed

That directory is **not** a factory codeplug. Its `r08` holds `FAM ALL D`,
`FAM TEAM 1 D` … and its `r04` holds contacts `Simplex` / `Eric` / `Jess` — the
family codeplug, not the vendor default.

The true factory state is `DCH 1`–`DCH 16` + `ACH 1`–`ACH 16` with a single
contact `Group 1` (1193046), which survives only as
`../../cps/cps_saves/retevis_matetalkp4_oem_cps_baseline_factory_20260812.dat`
and the CPS baseline serial capture. There is **no p64tool dump of the factory
state**.

`../README.md` calls that directory "Factory-fresh, unmodified radio" while also
saying it matches `P4_OEM_FAMILYPLAN_CPS_READAFTERWRITE_DUMP.txt` — the family
read-*after-write*. The second claim is the accurate one.

Consequence: any "diff vs factory baseline" in this repo, including the table in
`../p64tool_cm-p4-02_family_20260812/NOTES.md`, is really a diff against a
family codeplug on another unit. The comparisons are still valid, but they do not
show what changed from vendor defaults.
