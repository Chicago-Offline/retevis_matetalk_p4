# CM-P4-02 — family codeplug

Second reference dump. Same radio model and firmware as the factory baseline,
different physical unit, with the family codeplug flashed.

```
MCU name : DM5
Firmware : 1.0.0.0
Built    : 2025-06-23
Model    : P4 V1.2
```

13 regions, `header_ok=yes` on all, 53,381 bytes,
md5 `752c36ed1d61e5717ebf980e92a6c8b8`.

The handshake connected first try, three attempts for three. The other unit had
failed six consecutive handshakes on this same cable minutes earlier, which
confirms those failures were that radio and not the PL2303G or the driver.

## Diff vs `../p64tool_baseline_factory_20260812/`

Only **3 of 13 regions** differ.

| region | bytes differing | of |
|---|---|---|
| `r01` | 9 | 275 |
| `r03` | 2 | 51 |
| `r08` | 340 | 18451 |

Byte-identical: `r02`, `r04`, `r05`, `r06`, `r07`, `r0A`, `r32`, `rFF`, `rKL`,
**`rML`**.

### `rML` (sel `01 01`) is unchanged — useful negative result

The 16,531-byte undocumented region is byte-identical between a factory radio
and one with a full family codeplug flashed. The OEM CPS *writes* it, but
channel and zone programming does not alter it. Whatever it holds, it is not
channel/zone content. This narrows the mapping problem by elimination.

### `r01` looks like identity / serial

ASCII, at offset 0x40:

```
CM-P4-02 : 0260806080236
factory  : 0260812154651
```

Plus one byte at 0xE9 inside what appears to be a wide-char digit field
(`...0 1 6 7 7` vs `...0 1 6 7 0`).

### `r08` is the codeplug body

340 bytes changed, first differing byte at 410, last at 2238 (1-based). Changes
recur on a **~72-byte stride** — 410, 482, 554 — which is consistent with an
array of fixed-size channel records. Nothing past 2238 moved.

⚠️ **Record size and field layout are inferred from one sample and are NOT
established.** Do not build a decoder on the 72-byte figure until it is checked
against a second, differently-populated codeplug.

⚠️ `strings` finds nothing readable in `r08` in either dump, so channel names are
**not** stored there as ASCII or plain UTF-16LE — or they are not in `r08` at
all. Encoding is unknown; do not guess it from a single sample.

## Ground truth — read this before mapping

Eric describes the contents as **"the 6 family channels and 6 digital
equivalents"**, from
`muehlstein-codeplugger-profiles/profiles/retevis_matetalk_p4/yellow.yml`
**with the ham channels removed**.

🔴 **That does not match the profile as committed, and the discrepancy is
unresolved.** `yellow.yml`'s `family` zone lists **11** assignments, not 12:

```
asg_priv_fam_all, asg_priv_fam_team1, asg_priv_fam_team2,
asg_priv_fam_team3, asg_priv_fam_road, asg_priv_fam_repeater   (6 analog)
asg_priv_dmr_all, asg_priv_dmr_team1, asg_priv_dmr_team2,
asg_priv_dmr_team3, asg_priv_dmr_road                          (5 digital)
```

Six analog, **five** digital. The profile's own comment says
`11 channels: 6 analog GMRS + 5 DMR-on-GMRS`, and there is no
`asg_priv_dmr_repeater` — consistent with the repeater channel having no digital
counterpart.

So the radio holds either 11 or 12 channels depending on whether the profile or
the description is authoritative, and the two disagree. **Resolve this before
mapping the `r08` stride** — an off-by-one in the channel count will
mis-align every record boundary and produce a decoder that looks plausible and
is wrong.
