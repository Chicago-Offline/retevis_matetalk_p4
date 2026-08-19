# References — ReTevis MateTalk P4

Where to look things up, and which source wins on conflict.

## 🔴 Source precedence

For anything about the **codeplug byte map**, use upstream. Do not re-derive
offsets in this repo.

1. **[`oetiker/p64tool` → `docs/codeplug-format.md`](https://github.com/oetiker/p64tool/blob/main/docs/codeplug-format.md)**
   — authoritative. Decompiled vendor CPS cross-checked against live hardware
   dumps, with the dump winning on conflict.
2. **Live hardware dumps** — this repo's `p64tool_dumps/` and
   `cps/cps_serial_dumps/`, for confirming behavior on *our* firmware.
3. **Firmware image** — semantics and cross-checking only. See the caveat below.

## Upstream: `oetiker/p64tool`

<https://github.com/oetiker/p64tool> — MIT, Rust, "Linux programming tool for
the Retevis MateTalk P64 / P4 DMR radio".

Reads the codeplug as **13 regions** (`src/proto.rs` → `REGIONS`), decodes to an
editable `radio.toml`, re-encodes and writes back with post-write read-back
verification. Has a `roundtrip` self-test asserting byte-identical re-encode.

Region map, from `docs/codeplug-format.md`:

| region | contents |
|--------|----------|
| `r01`  | model / revision label |
| `r02`  | encryption |
| `r03`  | DMR network + radio DMR ID |
| `r04`  | contacts (200 x 40 @16) + RX-group lists (32 x 72 @8016) |
| `r05`  | emergency / digital-alarm (16 x 48 @16) + work-alone tail |
| `r06`  | scan lists (32 x 90 @16) |
| `r07`  | zones (16 x 68 @16) |
| `r08`  | channels (256 x 72 @16) |
| `r0A`  | alerts / man-down |
| `rML`  | quick-text (32 x 516 @16) |

⚠️ Upstream documents **two distinct offset coordinate systems** (CPS
record-relative vs. p64tool `rec[N]`) with a translation table. Read that before
interpreting any offset from either source.

⚠️ p64tool's `rKL` / `rML` **file names are unrelated** to the `KL` / `ML`
record prefixes in a CPS `.dat`. Map by selector via `manifest.txt` — see
`p64tool_dumps/README.md`.

### Identity and version gating

Live identity comes from a dedicated **`MCU-GET`** command (opcode `0x32`), not
from the 149-byte connect reply — both CPS and p64tool only prefix-match that
reply as an ACK. `"P64 V1.1"` / `"P64 V1.4"` is a **model-name/revision label**
stored in `r01`, **not** a firmware version. The CPS gates only on `"DM5"`.

## In this repo

| path | what it covers |
|------|----------------|
| `CODEPLUG.md` | The CPS `.dat` **save-file container** — the ASCII wrapper the CPS writes to disk. p64tool reads regions off the wire and never sees this format, so this is the part upstream does not describe. Includes the `-15` offset relationship between the two. |
| `p64tool_dumps/README.md` | Native p64tool region dumps, per-read. Provenance, verification, and the selector mapping table. |
| `UPSTREAM-P64TOOL-DRAFT.md` | Three findings drafted for upstream. **Not filed** — held pending a second radio. |
| `cps/cps_serial_dumps/` | OEM CPS read / write / read-after-write serial captures. |
| `cps/cps_saves/` | OEM CPS `.dat` save files. |

## Our hardware

```
MCU name : DM5
Firmware : 1.0.0.0
Built    : 2025-06-23
Model    : P4 V1.2
```

⚠️ **Outside upstream's validated set.** p64tool prints
`WARNING — P4 V1.2/1.0.0.0 not in p64tool's validated set`. Harmless for reads —
four consecutive reads were byte-identical, and all 13 regions matched the OEM
CPS readback of the same radio byte for byte. **Resolve before trusting the
write path.**

Upstream's map is validated on exactly one firmware version (`1.0.0.0` on both
their reference radios). They keep an allowlist and *warn* rather than block
outside it.

## Calibration: not in the codeplug

Settled, with a caveat about how strongly to state it.

- **No open-source tool reads P4 calibration.** p64tool is the only open tool
  for this radio; qdmr and NeonPlug have zero MateTalk/P4 support.
- `rFF` (619 B) is annotated upstream as *"Unknown (likely factory/calibration)
  — erased on default"*. On a stock radio it is ~95% `0xFF` (erased flash) with
  a small `00 01 00 02 00` header. Nothing to parse.
- `rFF` appears in both the read set and `WRITE_REGIONS`. Selector differs
  between the two: read uses `0xFFFF`, write frame bytes `[14..15]` use
  `0x00FF`. p64tool round-trips it **verbatim** — preserved, never interpreted.
- `r32` (51 B) and `rKL` (43 B) are likewise unknown and all-zero on a default
  codeplug.
- Upstream's version-gating spec states it directly: *"CPS writes all 13 regions
  it reads; there is no spared calibration region (calibration, if any, lives
  outside the read/write set and is never touched — same as p64tool)."*

So real calibration data most likely lives outside the codeplug address space
entirely — elsewhere in the AT32 flash, unreachable over the CPS protocol.

Contrast with our DM-32UV, where NeonPlug exposes a genuine read-only
77-parameter calibration snapshot (`src/radios/dm32uv/protocol.ts` →
`readCalibration()`). **There is no P4 equivalent.** Upside: correspondingly
lower risk of clobbering it, since neither CPS nor p64tool writes outside the 13
regions.

To identify `rFF`, upstream names the method: **differential dumps** — enable a
feature, re-read, diff.

## Firmware image

`dmr_dm5_1_0_0_0_..._Iap.bin` is an **Artery AT32** Cortex-M image in an IAP
container: 4096-byte header, then the raw image. Header offset 0 is payload
length (u32 LE); the image loads at flash `0x08000000`, so
`file_offset = flash_addr - 0x08000000 + 0x1000`. Unencrypted. Shares kernel
code with model `md440`; contains LittleFS, EasyLogger, the full DMR stack, and
`platform/db.c` (codeplug/database logic).

⚠️ **The firmware is not a shortcut to codeplug offsets.** It embeds no default
codeplug template, so offsets are not recoverable from strings — that would
require disassembling `db.c` (Cortex-M/Thumb). Its value is confirming field
*semantics* and cross-checking. The decompiled CPS remains authoritative.

## Regulatory note

p64tool targets the **P64** primarily; the P4 shares the tooling but is the
higher-power variant. Their `src/regs.rs` notes stock P64 "High" = 0.5 W (legal
PMR446), and that the 2 W mode requires the separate **P4 firmware upgrade,
which p64tool does not touch**.

Relevant because we are on the P4 in US Part 95/97 territory, not CEPT PMR446.
Upstream's only regulatory profile is `PMR446`, which is `simplex_only` with a
12.5 kHz cap — that does **not** describe our use.

## Open

- [ ] Second radio / second firmware. Every finding in
      `UPSTREAM-P64TOOL-DRAFT.md` is `n=1`.
- [ ] Decide whether a US regulatory profile belongs upstream (PR) or stays in
      a fork.
- [ ] Optional: differential `rFF` dumps to settle the calibration question.
