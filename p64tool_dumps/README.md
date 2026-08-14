# p64tool region dumps

Raw region dumps produced by [`p64tool`](https://github.com/oetiker/p64tool)
`read`, straight off the radio over the serial link. One directory per read.

These are the *native* p64tool artifact — 13 `rNN.bin` region files plus a
concatenated `codeplug_raw.bin` and a `manifest.txt`. They are not the CPS `.dat`
save format; see `../CODEPLUG.md` for that container and for the `−15` offset
relationship between the two.

## `p64tool_baseline_factory_20260812/`

🔴 **Misnamed — this is NOT factory state.** Its `r08` holds the *family*
codeplug (`FAM ALL D`, `FAM TEAM 1 D`, … `FAM RPTR`), the same channel set as
the two dumps explicitly labelled family. The "same codeplug state as
`P4_OEM_FAMILYPLAN_CPS_READAFTERWRITE_DUMP.txt`" line below is the accurate
one; "factory-fresh" was wrong and contradicts it. The data is good, the label
is not. For genuine factory state see `p64tool_purple_20260813/`.

Same physical unit and same codeplug state as
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

## `p64tool_purple_20260813/`

**The genuine factory-default codeplug** — 32 channels (`DCH 1`–`DCH 16` +
`ACH 1`–`ACH 16`), Serial No `123456789`, DMR ID `1`. 53,381 bytes, md5
`449156af5f89fa21c89af8799a61ffb1`, `header_ok=yes` on all 13 regions, two
independent reads byte-identical.

See its `NOTES.md` — it resolves the factory-serial and 11-vs-12-channel open
questions, corrects the mislabelled dump above, and identifies three bytes that
distinguish factory state from CPS-written state.

## `p64tool_blue_20260813/`

The blue radio, carrying the **full `yellow.yml` profile including the ham
channels** — 11 family channels plus 4 ham analog and 4 ham digital (hotspot).
DMR ID `3207125`. 53,381 bytes, md5 `15e3d29d9a2c6b2e445e8b8c38702465`,
`header_ok=yes` on all 13 regions, two independent reads byte-identical,
`roundtrip` OK.

**All 13 regions are byte-identical to `../cps/cps_serial_dumps/P4_BLUE_HAM_READ_DUMP.txt`**
— a second independent p64tool-vs-CPS parity check, on a different radio and
codeplug from the first.

## `p64tool_yellow_20260813/`

The yellow radio (`p4_02`, case serial ending 1677) — **11 family channels only**,
ham channels stripped, DMR ID `439`. 53,381 bytes, md5
`243d6bd67be5e2d7ec5cfb4f0aa46969`, `roundtrip` OK. Effectively unchanged from
`p64tool_p4_02_postwrite_selfid439_20260812` (4 bytes, all in `r01`).

Read back-to-back with the blue radio as a controlled two-radio test. Its
`NOTES.md` **settles the serial question**: both radios return byte-identical
149-byte connect replies despite being plainly different units, so the
connect-reply digit string is a model/firmware constant, not a hardware serial.
It also documents that blue's codeplug carries yellow's Serial No.

---

Blue's `NOTES.md` also carries an important correction: 🔴 **neither the r01 "Serial
No" nor the CONNECT-reply serial identifies a physical radio.** The first is
codeplug content that travels with the codeplug; the second is constant across
every unit observed. Do not infer "same serial, therefore same radio".

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

`rML.bin` (`sel=01 01`) is the second-largest region. It holds the **quick-text
message table** (32 records × 516 bytes at offset 16) — documented upstream in
p64tool's `docs/codeplug-format.md`; the earlier "not documented anywhere yet"
note here was stale.

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
