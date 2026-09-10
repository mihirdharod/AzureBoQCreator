#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Normalise a server-inventory workbook into a flat CSV for Azure BoQ pricing.

Handles the usual mess: every sheet names its columns differently, storage is
written as "1.1TB" / "610GB" / "2 TB - Premium SSD Managed Disks" / "?", and the
OS column is often missing entirely.

    python parse_inventory.py ServerList.xlsx --out inventory.csv
    python parse_inventory.py ServerList.xlsx --exclude ECP "SQL PAAS"

Emits one row per server with: sheet, app, vm, env, os, sku, cpu, ram,
storage_gb, storage_src, disk_type, is_prod, and reports every inference made.
"""
import argparse, csv, re, statistics, sys, unicodedata
from collections import defaultdict, Counter

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl required:  pip install openpyxl")

# Azure managed-disk tiers (GiB -> size code suffix)
TIERS = [(32, '4'), (64, '6'), (128, '10'), (256, '15'), (512, '20'),
         (1024, '30'), (2048, '40'), (4096, '50'), (8192, '60'),
         (16384, '70'), (32767, '80')]
PREFIX = {"premiumssd": "p", "standardssd": "e", "standardhdd": "s"}
LABEL = {"premiumssd": "Premium SSD", "standardssd": "Standard SSD",
         "standardhdd": "Standard HDD"}

# Column aliases, in priority order. Exact match first, then substring.
COLS = {
    "app":     ["Application name", "Server Name", "Cluster #", "Server Role"],
    "vm":      ["Server Name at Target", "Server Name (Actual)", "VM", "Server Name"],
    "env":     ["Workload Env", "Environment"],
    "os":      ["OS Version", "OS"],
    "sku":     ["Azure VM SKU", "VM Type at Target", "SKU Recommendation",
                "AMT Recommended (SKU)"],
    "cpu":     ["CPU at Source", "CPU", "vCPU"],
    "ram":     ["RAM at Source", "RAM [GB]", "Mem", "RAM"],
    "storage": ["Storage Disks at Target", "Storage Size [GB]",
                "Storage at Target", "Storage Disks at Source"],
    "media":   ["Storage Media"],
}


def clean(v):
    if v is None:
        return ""
    s = unicodedata.normalize("NFKC", str(v).replace("\xa0", " ").replace("\u202f", " "))
    return re.sub(r"\s+", " ", s).strip()


def find_col(headers, names):
    low = [h.lower() for h in headers]
    for n in names:                                    # exact
        if n.lower() in low:
            return low.index(n.lower())
    for n in names:                                    # substring
        for i, h in enumerate(low):
            if n.lower() in h:
                return i
    return None


def parse_gb(s):
    """'1.1TB' / '610GB' / '2 TB - Premium SSD' / '460' -> int GB, or None."""
    if not s or s.strip() in ("?", "-", "NA", "N/A"):
        return None
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(TB|GB)?", s, re.I)
    if not m:
        return None
    v = float(m.group(1).replace(",", ""))
    if (m.group(2) or "").upper() == "TB":
        v *= 1024
    return int(round(v))


def tier_for(gb):
    for cap, code in TIERS:
        if gb <= cap:
            return cap, code
    return 32767, '80'


def infer_os(os_text, vm_name, sheet):
    o = (os_text or "").lower()
    if "windows" in o:
        return "windows", "os column"
    if any(k in o for k in ("rhel", "linux", "ubuntu", "centos", "suse")):
        return "linux", "os column"
    n = (vm_name or "").upper()
    # naming convention: AZQW*/D1W* -> Windows, AZQL* -> Linux
    if re.match(r"^[A-Z]{2,4}W", n):
        return "windows", "name pattern"
    if re.match(r"^[A-Z]{2,4}L", n):
        return "linux", "name pattern"
    return "windows", "default"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("--out", default="inventory.csv")
    ap.add_argument("--exclude", nargs="*", default=[],
                    help="sheet names to skip (e.g. container/PaaS sheets)")
    ap.add_argument("--default-gb", type=int, default=256,
                    help="fallback when a sheet has no peers to infer from")
    a = ap.parse_args()

    wb = openpyxl.load_workbook(a.workbook, data_only=True)
    excl = {e.lower() for e in a.exclude}
    rows, skipped = [], []

    for ws in wb.worksheets:
        if ws.title.lower() in excl:
            skipped.append((ws.title, ws.max_row - 1))
            continue
        data = [[clean(c) for c in r] for r in ws.iter_rows(values_only=True)]
        if not data:
            continue
        # header is the first row that resolves a SKU column
        hdr_i = next((i for i in range(min(5, len(data)))
                      if find_col(data[i], COLS["sku"]) is not None), None)
        if hdr_i is None:
            skipped.append((ws.title, "no SKU column"))
            continue
        headers = data[hdr_i]
        idx = {k: find_col(headers, v) for k, v in COLS.items()}
        g = lambda r, k: (r[idx[k]] if idx[k] is not None and idx[k] < len(r) else "")

        for r in data[hdr_i + 1:]:
            if not any(r):
                continue
            sku = g(r, "sku")
            if not sku or sku.lower() in (s.lower() for s in COLS["sku"]):
                continue
            rows.append({
                "sheet": ws.title, "app": g(r, "app"), "vm": g(r, "vm"),
                "env": g(r, "env"), "os": g(r, "os"), "sku": sku,
                "cpu": g(r, "cpu"), "ram": g(r, "ram"),
                "storage_raw": g(r, "storage"), "media": g(r, "media"),
            })

    if not rows:
        sys.exit("No server rows found — check the workbook.")

    # peers for storage inference: same sheet + same application
    peers = defaultdict(list)
    for r in rows:
        gb = parse_gb(r["storage_raw"])
        if gb:
            peers[(r["sheet"], r["app"])].append(gb)

    inferred_os, inferred_gb = [], []
    for r in rows:
        r["is_prod"] = (r["env"] or "").strip().lower() in ("prod", "production")

        os_v, how = infer_os(r["os"], r["vm"], r["sheet"])
        r["os_final"] = os_v
        if how != "os column":
            inferred_os.append((r["sheet"], r["vm"], os_v, how))

        gb = parse_gb(r["storage_raw"])
        if gb is None:
            pl = sorted(peers.get((r["sheet"], r["app"]), []))
            gb = int(statistics.median(pl)) if pl else a.default_gb
            r["storage_src"] = f"median of {len(pl)} peers" if pl else "default"
            inferred_gb.append((r["sheet"], r["vm"], gb, r["storage_src"]))
        else:
            r["storage_src"] = "sheet"
        r["storage_gb"] = gb

        txt, media = r["storage_raw"], r["media"]
        if re.search(r"standard hdd", txt, re.I):
            dt = "standardhdd"
        elif re.search(r"standard ssd", txt, re.I) or "standardssd" in media.lower().replace(" ", ""):
            dt = "standardssd"
        elif re.search(r"premium ssd", txt, re.I) or "premiumssd" in media.lower().replace(" ", ""):
            dt = "premiumssd"
        else:
            dt = "premiumssd" if r["is_prod"] else "standardssd"
        cap, code = tier_for(gb)
        r["disk_type"], r["disk_cap_gib"], r["disk_code"] = dt, cap, PREFIX[dt] + code
        r["sku_calc"] = re.sub(r"_(v\d)$", r" \1", r["sku"].replace("Standard_", ""))
        r["label"] = f"{r['sheet']} | {r['vm'] or r['app']} | {r['sku_calc']} | {LABEL[dt]} ~{gb}GB"

    cols = ["sheet", "app", "vm", "env", "is_prod", "os_final", "sku", "sku_calc",
            "cpu", "ram", "storage_raw", "storage_gb", "storage_src",
            "disk_type", "disk_cap_gib", "disk_code", "label"]
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    # ---- report -------------------------------------------------------
    print(f"Wrote {a.out}  -  {len(rows)} servers\n")
    if skipped:
        print("Skipped sheets:")
        for s, why in skipped:
            print(f"  - {s} ({why})")
        print()
    print("Servers per sheet:")
    for k, v in Counter(r["sheet"] for r in rows).items():
        print(f"  {k:<28}{v:>4}")
    print(f"\nPROD {sum(r['is_prod'] for r in rows)}   "
          f"non-PROD {sum(not r['is_prod'] for r in rows)}")
    print("OS:", dict(Counter(r["os_final"] for r in rows)))
    print("Disk types:", dict(Counter(r["disk_type"] for r in rows)))
    print(f"Provisioned storage: {sum(r['disk_cap_gib'] for r in rows)/1024:.1f} TiB "
          f"(raw {sum(r['storage_gb'] for r in rows)/1024:.1f} TiB)")

    if inferred_gb:
        print(f"\n!! {len(inferred_gb)} servers had no storage size - CONFIRM THESE:")
        for sh, vm, gb, src in inferred_gb:
            print(f"   {sh:<24}{vm:<20}{gb:>6} GB   ({src})")
    if inferred_os:
        print(f"\n!! {len(inferred_os)} servers had no OS column - inferred:")
        for sh, vm, os_v, how in inferred_os[:20]:
            print(f"   {sh:<24}{vm:<20}{os_v:<9}({how})")
        if len(inferred_os) > 20:
            print(f"   ... and {len(inferred_os)-20} more")


if __name__ == "__main__":
    main()
