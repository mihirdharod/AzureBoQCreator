# Example inventory

`Northwind-Retail-Server-Inventory.xlsx` is the worked example used in
[TUTORIAL.md](../TUTORIAL.md).

**Northwind Retail is fictional.** Every hostname, application and figure is
invented — safe to share, screenshot, or use in a demo.

## Why it looks like this

It's deliberately messy, because real inventories are. Each awkward detail
exercises a specific behaviour:

| In the file | Exercises |
|---|---|
| Two sheets with completely different column names | fuzzy header matching |
| Storage as `1.5TB`, `600GB`, `2 TB - Premium SSD Managed Disks`, `?` | unit and free-text parsing |
| Three `?` storage cells | peer-median inference, reported per row |
| A sheet with **no OS column** | OS inference from naming convention |
| A container platform sheet | the "what's in scope" question |
| 6 PROD / 4 non-PROD | the pricing-term question |
| One F-series PROD server | the no-Reserved-Instance fallback |

## Contents

| Sheet | Servers | Notes |
|---|---|---|
| Storefront | 6 | full headers including OS |
| Warehouse | 4 | different headers, no OS column |
| Container Platform | 5 | usually excluded from a VM BoQ |

Ten servers are in scope once Container Platform is excluded — about 90 seconds
of build time, which is what makes this suitable for a demo.

## Regenerate

```bash
python examples/make_example_inventory.py
```

Edit that script to change the shape of the example.
