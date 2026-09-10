#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Recommend Azure VM SKUs from a SOURCE hardware inventory (no SKU column).

Use this when the workbook lists current physical/VM specs — CPU, RAM, disk, and
often utilisation — rather than target Azure SKUs. Typical headers:
Server | Physical or VM | OS | Environment | Total RAM GB | Peak RAM Utilization GB
| Total Disk GB/TB | Disk Utilization | Total CPU | MAX CPU Utilization

    python size_from_source.py "UAT sizing.xlsx" --mode rightsize --headroom 0.3
    python size_from_source.py "inventory.xlsx" --mode lift --region qatar-central

Modes
  rightsize  size to observed peak x (1 + headroom)   [needs utilisation columns]
  lift       size to provisioned specs x (1 + headroom)

Writes sized.csv and plan.json (ready to paste into the harness `runPlan`).
Always print the table and have the user confirm before building the estimate:
the lift-vs-rightsize choice can be a 4x cost difference.
"""
import argparse, csv, json, re, sys

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl required:  pip install openpyxl")

# (name, vCPU, RAM GiB, series rank) — rank orders price for equal vCPU: F < D < E
SERIES = [
    ("F", 1, [("F2s v2", 2, 4), ("F4s v2", 4, 8), ("F8s v2", 8, 16), ("F16s v2", 16, 32),
              ("F32s v2", 32, 64), ("F48s v2", 48, 96), ("F64s v2", 64, 128), ("F72s v2", 72, 144)]),
    ("D", 2, [("D2s v5", 2, 8), ("D4s v5", 4, 16), ("D8s v5", 8, 32), ("D16s v5", 16, 64),
              ("D32s v5", 32, 128), ("D48s v5", 48, 192), ("D64s v5", 64, 256), ("D96s v5", 96, 384)]),
    ("E", 3, [("E2s v5", 2, 16), ("E4s v5", 4, 32), ("E8s v5", 8, 64), ("E16s v5", 16, 128),
              ("E20s v5", 20, 160), ("E32s v5", 32, 256), ("E48s v5", 48, 384),
              ("E64s v5", 64, 512), ("E96s v5", 96, 672)]),
    ("M", 4, [("M32ls v2", 32, 256), ("M64ls v2", 64, 512), ("M64s v2", 64, 1024),
              ("M128s v2", 128, 2048)]),
]
SKUS = [(n, c, r, rank) for _, rank, lst in SERIES for n, c, r in lst]

TIERS = [(32, '4'), (64, '6'), (128, '10'), (256, '15'), (512, '20'), (1024, '30'),
         (2048, '40'), (4096, '50'), (8192, '60'), (16384, '70'), (32767, '80')]

COLS = {
    "server":   ["Server", "Server Name", "Hostname", "VM"],
    "os":       ["OS", "OS Version", "Operating System"],
    "env":      ["Environment", "Env"],
    "ram":      ["Total RAM GB", "RAM at Source", "RAM", "Memory"],
    "ram_pk":   ["Peak RAM Utilization GB", "Peak RAM", "RAM Utilization"],
    "disk":     ["Total Disk GB/TB", "Total Disk", "Storage", "Disk"],
    "disk_use": ["Disk Utilization", "Disk Used", "Used Disk"],
    "cpu":      ["Total CPU", "CPU at Source", "CPU", "vCPU", "Cores"],
    "cpu_pk":   ["MAX CPU Utilization", "Peak CPU Utilization", "CPU Utilization"],
}


def find(headers, names):
    low = [str(h or "").strip().lower() for h in headers]
    for n in names:
        if n.lower() in low:
            return low.index(n.lower())
    for n in names:
        for i, h in enumerate(low):
            if n.lower() in h:
                return i
    return None


def gb(v):
    """'1TB' / '8.79TB' / '755 GB' / '150G' / '650GB' / 64 -> float GB."""
    if v is None:
        return None
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(TB|GB|G|MB)?", str(v).strip(), re.I)
    if not m:
        return None
    val = float(m.group(1).replace(",", ""))
    u = (m.group(2) or "").upper()
    if u == "TB":
        val *= 1024
    elif u == "MB":
        val /= 1024
    return val


def num(v):
    m = re.search(r"([\d.]+)", str(v or ""))
    return float(m.group(1)) if m else None


def frac(v):
    """Utilisation may be 0.4 or '40%'. Return a 0-1 fraction."""
    s = str(v or "").strip()
    n = num(s)
    if n is None:
        return None
    if "%" in s or n > 1.0:
        return n / 100.0
    return n


def tier(g):
    for cap, code in TIERS:
        if g <= cap:
            return cap, code
    return 32767, '80'


def pick(tc, tr):
    c = [s for s in SKUS if s[1] >= tc and s[2] >= tr]
    c.sort(key=lambda s: (s[1], s[3], s[2]))
    return c[0] if c else None


def alt_down(chosen, pk_c, pk_r, min_head):
    c = [s for s in SKUS if s[1] < chosen[1]
         and s[1] >= pk_c * (1 + min_head) and s[2] >= pk_r * (1 + min_head)]
    c.sort(key=lambda s: (s[1], s[3], s[2]))
    return c[0] if c else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("--mode", choices=["rightsize", "lift"], default="rightsize")
    ap.add_argument("--headroom", type=float, default=0.30)
    ap.add_argument("--alt-headroom", type=float, default=0.20,
                    help="min headroom for the cheaper alternative column")
    ap.add_argument("--region", default="qatar-central")
    ap.add_argument("--billing", default="three-year")
    ap.add_argument("--prod-disk", default="premiumssd")
    ap.add_argument("--nonprod-disk", default="standardssd")
    ap.add_argument("--csv", default="sized.csv")
    ap.add_argument("--plan", default="plan.json")
    a = ap.parse_args()

    wb = openpyxl.load_workbook(a.workbook, data_only=True)
    rows = []
    for ws in wb.worksheets:
        data = [list(r) for r in ws.iter_rows(values_only=True)]
        if not data:
            continue
        hi = next((i for i in range(min(6, len(data)))
                   if find(data[i], COLS["server"]) is not None
                   and find(data[i], COLS["cpu"]) is not None), None)
        if hi is None:
            continue
        H = data[hi]
        idx = {k: find(H, v) for k, v in COLS.items()}
        g = lambda r, k: (r[idx[k]] if idx[k] is not None and idx[k] < len(r) else None)

        for r in data[hi + 1:]:
            srv = str(g(r, "server") or "").strip()
            if not srv or srv.lower().startswith("note"):
                continue
            cpu, ram = num(g(r, "cpu")), gb(g(r, "ram"))
            if not cpu or not ram:
                continue
            ram_pk, cpu_pk_f = gb(g(r, "ram_pk")), frac(g(r, "cpu_pk"))
            disk, disk_use = gb(g(r, "disk")), gb(g(r, "disk_use"))
            os_txt = str(g(r, "os") or "")
            os_v = "windows" if "windows" in os_txt.lower() else "linux"
            env = str(g(r, "env") or "").strip()
            is_prod = env.lower() in ("prod", "production")

            if a.mode == "rightsize" and ram_pk and cpu_pk_f:
                base_c, base_r, basis = cpu * cpu_pk_f, ram_pk, "peak"
            else:
                base_c, base_r, basis = cpu, ram, "provisioned"
            tc, tr = base_c * (1 + a.headroom), base_r * (1 + a.headroom)
            sku = pick(tc, tr)
            if not sku:
                print(f"!! no SKU fits {srv}: needs {tc:.0f} vCPU / {tr:.0f} GB", file=sys.stderr)
                continue
            alt = alt_down(sku, base_c, base_r, a.alt_headroom)

            dsrc = disk_use if (a.mode == "rightsize" and disk_use) else (disk or disk_use or 0)
            cap, code = tier(dsrc)
            dt = a.prod_disk if is_prod else a.nonprod_disk
            pfx = {"premiumssd": "p", "standardssd": "e", "standardhdd": "s"}[dt]

            rows.append(dict(
                sheet=ws.title.replace(" UAT", "").strip(), server=srv, os=os_v, os_txt=os_txt,
                env=env or "UAT", basis=basis,
                src_cpu=cpu, src_ram=ram, src_disk=disk,
                pk_cpu=round(base_c, 1), pk_ram=base_r, disk_use=disk_use,
                tgt_cpu=round(tc, 1), tgt_ram=round(tr, 1),
                sku=sku[0], sku_cpu=sku[1], sku_ram=sku[2],
                alt=(alt[0] if alt else ""),
                disk_gib=cap, disk_type=dt, disk_code=pfx + code))

    if not rows:
        sys.exit("No server rows found — check the workbook headers.")

    with open(a.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    LBL = {"premiumssd": "Premium SSD", "standardssd": "Standard SSD", "standardhdd": "Standard HDD"}
    plan = [{"l": f"{x['sheet']} | {x['server']} | {x['sku']} | {LBL[x['disk_type']]} "
                  f"~{int(x['disk_use'] or x['src_disk'] or 0)}GB",
             "s": x["sku"], "o": x["os"], "r": a.region, "n": 1, "b": a.billing,
             "ahb": False, "t": x["disk_type"], "c": x["disk_code"], "dn": 1}
            for x in rows]
    json.dump(plan, open(a.plan, "w"), separators=(",", ":"))

    hdr = (f"{'SERVER':<20}{'OS':<9}{'SRC cpu/RAM':<14}{'BASIS':<12}"
           f"{'TARGET':<12}{'AZURE SKU':<12}{'vCPU/RAM':<11}{'DISK':<16}{'CHEAPER ALT'}")
    print(f"mode={a.mode}  headroom=+{a.headroom:.0%}  region={a.region}  billing={a.billing}\n")
    print(hdr); print("-" * len(hdr))
    for x in rows:
        src = f"{x['src_cpu']:.0f}/{x['src_ram']:.0f}"
        basis = f"{x['pk_cpu']:.0f}/{x['pk_ram']:.0f} {x['basis'][:4]}"
        tgt = f"{x['tgt_cpu']:.0f}/{x['tgt_ram']:.0f}"
        got = f"{x['sku_cpu']}/{x['sku_ram']}"
        dsk = f"{x['disk_gib']}GiB {x['disk_code'].upper()}"
        print(f"{x['server']:<20}{x['os']:<9}{src:<14}{basis:<12}"
              f"{tgt:<12}{x['sku']:<12}{got:<11}{dsk:<16}{x['alt']}")
    print("-" * len(hdr))
    print(f"{len(rows)} servers | SOURCE {sum(x['src_cpu'] for x in rows):.0f} cpu, "
          f"{sum(x['src_ram'] for x in rows):.0f} GB RAM")
    print(f"{'':12}| AZURE  {sum(x['sku_cpu'] for x in rows)} vCPU, "
          f"{sum(x['sku_ram'] for x in rows)} GB RAM, "
          f"{sum(x['disk_gib'] for x in rows)/1024:.1f} TiB")
    print(f"\nWrote {a.csv} and {a.plan}")
    print("CONFIRM the sizing table with the user before building the estimate.")
    if any(x["sku"].startswith("F") for x in rows):
        print("NOTE: F-series has no Reserved Instance — those rows fall back to a Savings Plan.")


if __name__ == "__main__":
    main()
