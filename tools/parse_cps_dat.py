#!/usr/bin/env python3
"""Decode a Retevis MateTalk P4 OEM CPS `.dat` save file.

The `.dat` is an ASCII wrapper (see CODEPLUG.md); each record payload is the
region bytes, so the CPS record-relative offsets documented in p64tool's
docs/codeplug-format.md apply directly to a record payload.

Usage: tools/parse_cps_dat.py cps/cps_saves/<file>.dat [--json]
"""

import argparse
import json
import re
import sys

REC = re.compile(r"^(.{6}) (\d{5})=(.*?)\s*$")

# p64tool's doc says byte 33 &0x03 is 0=low/2=high; the CPS shows the opposite
# (bits 0 = High, bits 2 = Low), confirmed against a codeplug read back off the radio.
POWER = {0: "high", 1: "mid", 2: "low"}
ADMIT = {0: "always", 1: "channel-free", 2: "color-code-free", 3: "correct-cc"}
# Confirmed against the CPS dropdown; only values 0 and 2 seen in the wild.
BANDWIDTH = {0: "12.5k", 1: "20k", 2: "25k"}
CALL_TYPE = {0: "private", 1: "group", 2: "all"}


def parse_dat(path):
    """Return (header, [(key, offset, bytes), ...])."""
    with open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8", "replace")

    header, records = None, []
    for line in text.splitlines():
        if not line.strip():
            continue
        if header is None and line.startswith("Model="):
            header = line.strip()
            continue
        m = REC.match(line)
        if not m:
            raise ValueError(f"unparsable line: {line!r}")
        key, off, payload = m.group(1), int(m.group(2)), m.group(3)
        records.append((key, off, bytes(int(b, 16) for b in payload.split())))
    return header, records


def u16(b, o):
    return int.from_bytes(b[o:o + 2], "little")


def u32(b, o):
    return int.from_bytes(b[o:o + 4], "little")


def name(b, o=0, n=32):
    return b[o:o + n].split(b"\xff")[0].decode("utf-16-le", "replace").split("\x00")[0]


def tone(b, o):
    lo, hi = b[o], b[o + 1]
    if (lo, hi) == (0xFF, 0xFF):
        return None
    val = (hi & 0x0F) * 256 + lo
    kind = hi & 0xC0
    if kind == 0x00:
        return f"{val / 10:.1f}"
    return f"D{val:03o}{'N' if kind == 0x80 else 'I'}"


def members(b, off, count, cap=16):
    out = []
    for i in range(min(count, cap)):
        v = u16(b, off + i * 2)
        if v in (0, 0xFFFF):
            continue
        out.append(v)
    return out


def decode_channel(b):
    digital = b[32] == 0
    flags = b[33]
    ch = {
        "name": name(b),
        "mode": "digital" if digital else "analog",
        "rx_hz": u32(b, 36),
        "tx_hz": u32(b, 40),
        "power": POWER.get(flags & 0x03, flags & 0x03),
        "tx_admit": ADMIT.get((flags & 0x30) >> 4),
        "rx_only": bool(flags & 0x40),
        "record": u16(b, 70),
    }
    if digital:
        ch.update(
            contact_idx=u16(b, 48),
            rx_group_idx=u16(b, 50),
            color_code=b[52] & 0x0F,
            time_slot=2 if b[52] & 0x20 else 1,
            scan_list_idx=b[58],
        )
    else:
        ch.update(
            bandwidth=BANDWIDTH.get((flags & 0x0C) >> 2),
            rx_tone=tone(b, 58),
            tx_tone=tone(b, 60),
            scan_list_idx=b[54],
        )
    return ch


def decode_zone(b):
    n = u16(b, 34)
    return {"name": name(b), "count": n, "members": members(b, 36, n)}


def decode_scanlist(b):
    # Slot 58 is the "Current Channel" entry the CPS always shows and does not
    # let you remove; it is stored as 0 and IS counted by the u16 at 56. Real
    # channel members follow at 60. An empty list is therefore count=1.
    total = u16(b, 56)
    def opt(o):
        v = u16(b, o)
        return None if v == 0xFFFF else v
    return {
        "name": name(b),
        "tx_designated": opt(34),
        "priority1": opt(36),
        "priority2": opt(38),
        "count": total,
        "current_channel": u16(b, 58) == 0,
        "members": members(b, 60, max(total - 1, 0), cap=15),
    }


def decode_contact(b):
    return {"name": name(b), "dmr_id": u32(b, 32) & 0xFFFFFF, "type": CALL_TYPE.get(b[36], b[36])}


def decode_rxgroup(b):
    n = b[64]
    return {"name": name(b), "count": n, "members": members(b, 32, n)}


def decode(path):
    header, records = parse_dat(path)
    out = {
        "file": path,
        "header": header,
        "record_count": len(records),
        "channels": [],
        "zones": [],
        "scan_lists": [],
        "contacts": [],
        "rx_groups": [],
    }
    for key, _off, payload in records:
        if key.startswith("08CH"):
            out["channels"].append(decode_channel(payload))
        elif key.startswith("07E0"):
            out["zones"].append(decode_zone(payload))
        elif key.startswith("06E1"):
            out["scan_lists"].append(decode_scanlist(payload))
        elif key.startswith("04E4"):
            out["contacts"].append(decode_contact(payload))
        elif key.startswith("04E5"):
            out["rx_groups"].append(decode_rxgroup(payload))
    return out


def mhz(hz):
    return f"{hz / 1e6:.4f}"


def report(cp):
    ch = cp["channels"]
    print(f"{cp['file']}  [{cp['header']}]  {cp['record_count']} records")
    print(f"\nCHANNELS ({len(ch)})")
    print(f"{'#':>3} {'name':<16} {'md':<4} {'rx':>9} {'tx':>9} {'pwr':<5} "
          f"{'rxonly':<6} {'rxtone':>7} {'txtone':>7} {'cc/bw':<6} {'scan':>4}")
    for i, c in enumerate(ch, 1):
        if c["mode"] == "digital":
            extra = f"cc{c['color_code']}/s{c['time_slot']}"
            rxt = txt = "-"
        else:
            extra = c["bandwidth"] or "?"
            rxt, txt = c["rx_tone"] or "-", c["tx_tone"] or "-"
        print(f"{i:>3} {c['name']:<16} {c['mode'][:4]:<4} {mhz(c['rx_hz']):>9} "
              f"{mhz(c['tx_hz']):>9} {c['power']:<5} {str(c['rx_only']):<6} "
              f"{rxt:>7} {txt:>7} {extra:<6} {c['scan_list_idx']:>4}")

    def chname(idx):
        return ch[idx - 1]["name"] if 1 <= idx <= len(ch) else f"?{idx}"

    print(f"\nZONES ({len(cp['zones'])})")
    for z in cp["zones"]:
        print(f"  {z['name']} ({z['count']}): " + ", ".join(f"{m}:{chname(m)}" for m in z["members"]))

    print(f"\nSCAN LISTS ({len(cp['scan_lists'])})")
    for s in cp["scan_lists"]:
        print(f"  {s['name']} ({s['count']}) tx={s['tx_designated']} "
              f"p1={s['priority1']} p2={s['priority2']}")
        entries = (["<Current Channel>"] if s["current_channel"] else []) + \
                  [f"{m}:{chname(m)}" for m in s["members"]]
        print("    " + ", ".join(entries))

    if cp["contacts"]:
        print(f"\nCONTACTS ({len(cp['contacts'])})")
        for c in cp["contacts"]:
            print(f"  {c['name']:<16} {c['dmr_id']:<10} {c['type']}")

    if cp["rx_groups"]:
        print(f"\nRX GROUPS ({len(cp['rx_groups'])})")
        for g in cp["rx_groups"]:
            print(f"  {g['name']} ({g['count']}): {g['members']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dat", nargs="+")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args()

    for path in args.dat:
        cp = decode(path)
        if args.json:
            json.dump(cp, sys.stdout, indent=2)
            print()
        else:
            report(cp)
            print()


if __name__ == "__main__":
    main()
