#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Impact model for the Azure BoQ Creator Skill.

Every assumption is a flag, so the model can be argued with rather than
taken on faith. See IMPACT.md for where each default comes from.

    python tools/impact_model.py
    python tools/impact_model.py --vms 200 --scenarios 4 --boqs-per-year 15
    python tools/impact_model.py --sec-per-click 3 --setup-min 10   # pessimistic
"""
import argparse


def manual_minutes(vms, scenarios, clicks_per_vm, sec_per_click):
    """All of this is keyboard time."""
    return vms * clicks_per_vm * sec_per_click * scenarios / 60


def skill_minutes(vms, scenarios, sec_per_row, setup_min):
    """Mostly unattended - the driver runs while you do something else."""
    return (vms * sec_per_row * scenarios / 60) + (setup_min * scenarios)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--vms", type=int, default=95,
                   help="servers in the estate (default: 95)")
    p.add_argument("--scenarios", type=int, default=3,
                   help="times the BoQ gets re-priced (default: 3)")
    p.add_argument("--boqs-per-year", type=int, default=10,
                   help="BoQs you produce annually (default: 10)")
    p.add_argument("--clicks-per-vm", type=int, default=20,
                   help="MEASURED from the fields the harness sets (default: 20)")
    p.add_argument("--sec-per-click", type=float, default=4.0,
                   help="ASSUMPTION incl. reading and page settle (default: 4)")
    p.add_argument("--sec-per-row", type=float, default=7.0,
                   help="MEASURED driver time per row (default: 7)")
    p.add_argument("--setup-min", type=float, default=5.0,
                   help="ASSUMPTION: setup + review per scenario (default: 5)")
    a = p.parse_args()

    print("\nINPUTS")
    print("-" * 58)
    print(f"  estate                {a.vms} VMs")
    print(f"  scenarios per BoQ     {a.scenarios}")
    print(f"  BoQs per year         {a.boqs_per_year}")
    print(f"  clicks per VM         {a.clicks_per_vm}      (measured)")
    print(f"  seconds per click     {a.sec_per_click}       (assumption)")
    print(f"  driver sec per row    {a.sec_per_row}       (measured)")
    print(f"  setup+review          {a.setup_min} min   (assumption)")

    print("\nPER BoQ")
    print("-" * 58)
    print(f"  {'ESTATE':>7} {'SCEN':>5} {'MANUAL':>9} {'SKILL':>9} {'SAVED':>9} {'RATIO':>6}")
    for vms in sorted({25, 50, 95, 200, a.vms}):
        for sc in sorted({1, a.scenarios}):
            m = manual_minutes(vms, sc, a.clicks_per_vm, a.sec_per_click)
            s = skill_minutes(vms, sc, a.sec_per_row, a.setup_min)
            mark = "  <-- yours" if (vms == a.vms and sc == a.scenarios) else ""
            print(f"  {vms:>7} {sc:>5} {m:>7.0f}m {s:>7.0f}m {m - s:>7.0f}m "
                  f"{m / s:>5.1f}x{mark}")

    m = manual_minutes(a.vms, a.scenarios, a.clicks_per_vm, a.sec_per_click)
    s = skill_minutes(a.vms, a.scenarios, a.sec_per_row, a.setup_min)
    saved = m - s

    print("\nYOUR CASE")
    print("-" * 58)
    print(f"  manual                {m / 60:>6.1f} h per BoQ   (all keyboard time)")
    print(f"  with skill            {s / 60:>6.1f} h per BoQ   (mostly unattended)")
    print(f"  saved                 {saved / 60:>6.1f} h per BoQ")
    print()
    print(f"  annual, {a.boqs_per_year} BoQs      {saved * a.boqs_per_year / 60:>6.0f} h returned")
    print(f"  = working days        {saved * a.boqs_per_year / 60 / 8:>6.1f} d")

    print("\nNOT COUNTED (the model is a floor, not a ceiling)")
    print("-" * 58)
    print("  - finding and fixing a mis-priced line by hand")
    print("  - context switching across a 2-hour clicking task")
    print("  - rework when an export silently returns stale data")
    print("  - the value of catching a $602/mo line priced at $0.00")
    print()


if __name__ == "__main__":
    main()
