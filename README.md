# Azure BoQ Creator Agent

Converts any server or resource inventory into a priced Azure Bill of Quantities.
Right-sizes VMs from utilisation data, prices compute, storage, databases and
networking on the Azure Pricing Calculator, verifies every line item, and exports
a client-ready Excel BoQ with a per-application cost summary.

A skill for the **GitHub Copilot app**.

---

## Why

Building a BoQ by hand means opening the Azure Pricing Calculator and clicking
through one row per server. For 95 servers that is a long afternoon, and the
errors it produces are the dangerous kind — a line item silently priced at $0.00
looks fine inside a plausible-looking total.

This skill automates the mechanical part and, more importantly, **audits the
result** for the failures a total hides.

## What it does

1. **Reads the inventory** — detects whether the workbook already has Azure SKUs
   (a target list) or is raw source hardware, and routes accordingly.
2. **Sizes the VMs** — for source hardware, recommends SKUs from CPU/RAM, using
   observed peak utilisation where available. Suggests a cheaper alternative
   wherever one size down still clears peak with headroom.
3. **Asks the commercial questions** — lift-and-shift vs right-size, pricing
   term, Azure Hybrid Benefit, region. These move cost more than anything else,
   so they are never assumed.
4. **Builds the estimate** — drives the Azure Pricing Calculator in a browser
   canvas. Works for any of its ~222 products, not just VMs.
5. **Verifies** — re-reads every row and flags zero-cost items, labels that don't
   match their configuration, and region fields left at defaults.
6. **Exports** — an Excel BoQ with a formatted Summary sheet: cost by
   application, service category, region and pricing model.

## Install

Copy the folder into the Copilot app's skills directory:

**Windows**
```powershell
Copy-Item -Recurse .\azure-boq-creator-agent `
  "$env:APPDATA\com.github.githubapp\app-skills\"
```

**macOS / Linux**
```bash
cp -r ./azure-boq-creator-agent \
  ~/Library/Application\ Support/com.github.githubapp/app-skills/
```

Restart the app, or start a new session. Python scripts need `openpyxl`:

```bash
pip install openpyxl
```

## Use

Attach a server list and ask for a BoQ:

> Build me an Azure BoQ from this server list, priced in West Europe.

The skill will confirm scope and commercial assumptions, then build, verify and
export the estimate.

## Layout

```
azure-boq-creator-agent/
├── SKILL.md                     workflow the agent follows
├── reference/
│   ├── calculator-dom.md        selectors, React quirks, 12 failure modes
│   └── products.md              schemas for non-VM services
└── scripts/
    ├── parse_inventory.py       target list  → normalised CSV
    ├── size_from_source.py      source hardware → SKU recommendations
    ├── harness.js               browser driver for the calculator
    └── build_summary.py         exported estimate → Excel summary sheet
```

## Design notes

**Schema discovery over hardcoding.** The calculator has ~222 products but they
all share one DOM shape — only field names differ. Rather than encode each
product, the harness reads a row's schema at runtime (`__describeRow` returns
field names *and* their legal option values) and configures it generically. That
means it handles services the author never tested.

**Verification is the point.** Automating the clicking is the easy half.
`reference/calculator-dom.md` documents 12 failure modes found by building real
estimates, including several that produce a wrong number rather than an error:

- Changing region silently reverts a reservation to pay-as-you-go.
- Some SKUs (Fsv2) have no Reserved Instance at all — the skill falls back to a
  Savings Plan and says so rather than quietly pricing full rate.
- Selecting a region/redundancy pair the region doesn't support removes the
  pricing fields instead of raising an error.
- Quantities are entered in **GB**: "5 TB" means 5120. Defaults like Bandwidth's
  5 GB from us-west price at $0.00 because of the free tier.

That last one was a real bug caught in testing — a Bandwidth row labelled "5 TB"
was contributing **$0/month** to an estimate where it should have been $602, or
24% of the total. `__auditCosts()` now catches that class of error.

**Ask, don't assume.** Lift-and-shift versus right-sizing changed one pair of
servers from `M128s v2` (128 vCPU / 2 TB RAM) to `E32s v5` — roughly a 4x cost
difference. The skill surfaces that choice rather than picking one.

## Validation

| Inventory | Result |
|---|---|
| 9 sheets, 95 VMs across 9 applications | $113,921/mo · $1.37M/yr — built, verified, exported |
| 3 sheets, 10 physical servers with utilisation data | Right-sized 608 → 536 vCPU, 2,038 → 1,456 GB RAM |
| Mixed VM + Storage + Files + SQL + Bandwidth | All 5 services priced and summarised |

## Notes

Prices are estimates from the public Azure Pricing Calculator and exclude VAT,
customer-specific agreement discounts, and anything outside the agreed scope.
Always confirm inferred values — storage sizes, OS, environment — before a BoQ
goes to a customer.
