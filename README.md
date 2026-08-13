# ReTevis MateTalk P4

Vendor programming software and firmware for the ReTevis MateTalk P4, plus our
own hardware dumps and notes on the parts upstream does not cover.

## 🔴 Start here

For the **codeplug byte map**, use upstream — do not re-derive offsets here:
**[`oetiker/p64tool` → `docs/codeplug-format.md`](https://github.com/oetiker/p64tool/blob/main/docs/codeplug-format.md)**

`REFERENCES.md` explains what upstream covers, what we cover, and which source
wins on conflict.

## Contents

| path | what it is |
|------|------------|
| `REFERENCES.md` | Source precedence, upstream region map, our hardware/firmware, calibration findings, regulatory note. |
| `CODEPLUG.md` | The CPS `.dat` **save-file container** — the ASCII wrapper the CPS writes to disk, and the `-15` offset relationship to p64tool regions. Upstream reads off the wire and never sees this format. |
| `p64tool_dumps/` | Native p64tool region dumps (13 `rNN.bin` + `codeplug_raw.bin` + `manifest.txt`), one directory per read. See its `README.md` for provenance and the selector mapping. |
| `cps/cps_serial_dumps/` | OEM CPS read / write / read-after-write serial captures. |
| `cps/cps_saves/` | OEM CPS `.dat` save files. |
| `cps/P4-Programming-Software.zip` | Windows programming software. |
| `firmware/P4-64-Firmware.zip` | Firmware image. |
| `UPSTREAM-P64TOOL-DRAFT.md` | Three findings drafted for upstream. **Not filed** — held pending a second radio. |

## Our radio

```
MCU name : DM5
Firmware : 1.0.0.0
Built    : 2025-06-23
Model    : P4 V1.2
```

⚠️ **Outside upstream's validated set** — p64tool warns
`P4 V1.2/1.0.0.0 not in p64tool's validated set`. Harmless for reads: four
consecutive reads were byte-identical, and all 13 regions matched the OEM CPS
readback of the same radio byte for byte. **Resolve before trusting the write
path.**

## Calibration is not in the codeplug

Short version: `rFF` is ~95% erased flash on a stock radio, p64tool round-trips
it verbatim without interpreting it, and upstream states there is no spared
calibration region. Real calibration data most likely lives outside the codeplug
address space entirely, unreachable over the CPS protocol. Unlike our DM-32UV,
there is **no P4 calibration read**. Details and sources in `REFERENCES.md`.

## Notes

- No custom firmware build and no full RE implementation here — that is upstream.
- Use the programming software and firmware only with compatible hardware.
- Back up radio settings before flashing or reprogramming.
