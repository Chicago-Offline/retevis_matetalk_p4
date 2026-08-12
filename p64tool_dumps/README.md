# p64tool region dumps

Raw region dumps produced by [`p64tool`](https://github.com/oetiker/p64tool)
`read`, straight off the radio over the serial link. One directory per read.

These are the *native* p64tool artifact — 13 `rNN.bin` region files plus a
concatenated `codeplug_raw.bin` and a `manifest.txt`. They are not the CPS `.dat`
save format; see `../CODEPLUG.md` for that container and for the `−15` offset
relationship between the two.

## `p64tool_baseline_factory_20260812/`

Factory-fresh, unmodified radio. Same physical unit and same codeplug state as
`../cps/cps_serial_dumps/P4_OEM_FAMILYPLAN_CPS_READAFTERWRITE_DUMP.txt`.

```
MCU name : DM5
Firmware : 1.0.0.0
Built    : 2025-06-23
Model    : P4 V1.2
```

Read on macOS (Apple silicon) via the in-box Prolific PL2303G cable at
115200 8N1. 53,381 bytes total, `header_ok=yes` on all 13 regions.

**Verified:** four consecutive reads were byte-identical to each other
(`md5 568fd392bd332d97f134019305440517`), and **all 13 regions are
byte-identical to the OEM CPS readback capture** of the same radio. p64tool and
the vendor CPS pull the same bytes.

⚠️ p64tool prints `WARNING — P4 V1.2/1.0.0.0 not in p64tool's validated set`.
Harmless for reads. **Resolve it before trusting the write path** against this
firmware.

### Region file names do not match the CPS `.dat` record keys

p64tool's `rKL` / `rML` filenames are **not** related to the `KL` / `ML` record
prefixes in a CPS `.dat`. Map by selector, from `manifest.txt`:

| file | selector | bytes |
|---|---|---|
| `r01.bin` | `01 00` | 275 |
| `r02.bin` | `02 00` | 2187 |
| `r03.bin` | `03 00` | 51 |
| `r04.bin` | `04 00` | 10323 |
| `r05.bin` | `05 00` | 791 |
| `r06.bin` | `06 00` | 2899 |
| `r07.bin` | `07 00` | 1107 |
| `r08.bin` | `08 00` | 18451 |
| `rFF.bin` | `ff ff` | 619 |
| `r32.bin` | `32 00` | 51 |
| `r0A.bin` | `0a 00` | 53 |
| `rKL.bin` | `00 01` | 43 |
| `rML.bin` | `01 01` | **16531** |

`rML.bin` (`sel=01 01`) is the second-largest region and is **not documented**
in p64tool's `REGIONS` table or anywhere else yet. The CPS writes it, so it
carries real codeplug content. Unmapped — good target for analysis.

## Reproducing a read

```bash
p64tool info --port /dev/cu.PL2303G-USBtoUART21x0          # liveness check
p64tool read --port /dev/cu.PL2303G-USBtoUART21x0 --out p64-dump
```

⚠️ **The first connect after the port has been idle returns 0 bytes.** Immediately
retrying succeeds, and the link is then stable across many operations. This is
not a baud, cable, or modem-line problem — do not go chasing one. Just retry.

macOS note: the Prolific PL2303G needs its DriverKit extension **enabled** under
System Settings → General → Login Items & Extensions → **Driver Extensions**. A
dext left in `[activated waiting for user]` enumerates a working-looking
`/dev/cu.*` but silently fails `TIOCMSET`, so DTR/RTS never assert and the radio
stays silent. Check with `systemextensionsctl list`.
