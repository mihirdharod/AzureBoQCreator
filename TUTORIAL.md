# Tutorial — build your first Azure BoQ

A complete walkthrough, from installing the skill to a finished Excel Bill of
Quantities. Roughly 10 minutes end to end.

There's a worked example inventory in [`examples/`](examples/) so you can follow
along exactly, before pointing it at your own data.

---

## What you'll build

From a messy three-sheet server inventory, you'll produce:

- a priced estimate on the Azure Pricing Calculator, one line item per server
- an Excel BoQ with cost by application, service category, region and pricing model
- a stated list of every assumption the skill had to make

---

## 1. Prerequisites

- The **GitHub Copilot app** (this is a skill for it, not a standalone tool)
- **Python 3.9+** with `openpyxl` — `pip install openpyxl`
- A browser canvas, which the app provides

---

## 2. Install

Clone the repo and copy the skill folder into the app's skills directory.

**Windows**
```powershell
git clone https://github.com/mihirdharod/AzureBoQCreator.git
cd AzureBoQCreator
Copy-Item -Recurse .\azure-boq-creator-skill "$env:APPDATA\com.github.githubapp\app-skills\"
```

**macOS / Linux**
```bash
git clone https://github.com/mihirdharod/AzureBoQCreator.git
cd AzureBoQCreator
cp -r ./azure-boq-creator-skill ~/Library/Application\ Support/com.github.githubapp/app-skills/
```

Then **start a new session**. Skills load at session start, so the one you're in
now won't see it.

Verify it's there:

```powershell
Get-ChildItem "$env:APPDATA\com.github.githubapp\app-skills\azure-boq-creator-skill"
```

You should see `SKILL.md`, `reference/` and `scripts/`.

---

## 3. Run the walkthrough

Attach [`examples/Northwind-Retail-Server-Inventory.xlsx`](examples/Northwind-Retail-Server-Inventory.xlsx)
and ask:

> Build me an Azure BoQ from this inventory, priced in West Europe.

That's the whole prompt. What follows is what the skill does, and why.

### 3.1 It reads the inventory and tells you what it inferred

The example has 15 servers across three sheets, and is deliberately messy —
because real inventories are:

| Sheet | Servers | What makes it awkward |
|---|---|---|
| Storefront | 6 | storage written `1.5TB`, `600GB`, `2 TB - Premium SSD Managed Disks`, `?` |
| Warehouse | 4 | completely different column names, **no OS column at all** |
| Container Platform | 5 | an OpenShift-style cluster, usually priced separately |

You'll get a report like this:

```
Wrote inventory.csv  -  10 servers

Skipped sheets:
  - Container Platform (5)

PROD 6   non-PROD 4
OS: {'windows': 8, 'linux': 2}
Provisioned storage: 11.0 TiB (raw 8.8 TiB)

!! 3 servers had no storage size - CONFIRM THESE:
   Storefront   NWAZLDBQ01     600 GB   (median of 5 peers)
   Warehouse    NWAZWWMSD01    800 GB   (median of 2 peers)
   Warehouse    NWAZWRPT01     800 GB   (median of 2 peers)

!! 4 servers had no OS column - inferred:
   Warehouse    NWAZWWMS01     windows  (name pattern)
```

Two things worth understanding here.

**`?` storage is inferred from peers, not a global default.** A server with no
size inherits the median of the *other servers in its own application*, and every
one is listed so you can correct it. A blanket 256 GB default would be invisible
and wrong.

**Missing OS is read from the naming convention.** `NWAZW…` is Windows,
`NWAZL…` is Linux. It tells you when it did this, so you can override.

### 3.2 It asks before it prices

The skill will ask you three things. **These move cost more than anything else,
which is why they're never assumed:**

| Question | For this walkthrough, answer |
|---|---|
| Which sheets are in scope? | Exclude **Container Platform** |
| Pricing term? | **3-year Reserved Instance for PROD, pay-as-you-go for non-PROD** |
| Azure Hybrid Benefit? | **No** |

On Hybrid Benefit: if the customer has Windows Server licences with Software
Assurance, applying it typically cuts Windows VM cost by around 40%. Getting this
wrong is a large, silent error.

### 3.3 It builds the estimate

The Azure Pricing Calculator has no import API, so the skill drives its DOM in a
browser canvas — one line item per server, named
`Application | Server | SKU | Disk`, so every row traces back to the inventory.

Ten servers takes about 90 seconds. You'll see it work through them.

Watch for this in the output:

> `Standard_F8s_v2` has no Reserved Instance — falling back to a 3-year Savings Plan

Azure genuinely doesn't offer RIs for the Fsv2 family. Rather than quietly
pricing it at full rate, the skill substitutes the nearest equivalent commitment
and tells you which rows and why.

### 3.4 It verifies before quoting

This is the part that matters most. Before reporting any total, the skill reads
every row back and audits it:

| Check | Catches |
|---|---|
| `ZERO_COST` | a line item priced $0.00 — usually an unset quantity |
| `LABEL_QTY_NOT_IN_ROW` | label says "5 TB" but the row isn't configured for it |
| `REGION_MISMATCH` | a region field left at its default |

You want to see `verified, 0 mismatches`.

These aren't theoretical. A bandwidth line labelled "5 TB" was once sitting at
the default 5 GB in the wrong region, pricing at **$0.00** — $602/month, 24% of
that estimate, completely invisible inside a total that looked fine.

### 3.5 It exports the BoQ

You get an Excel workbook with two sheets:

- **Summary** — KPI block, then cost by application, service category, region and
  pricing model
- **The line items** — every server, its SKU, region, description and monthly cost

Figures are written as static values rather than cross-sheet formulas. A BoQ is a
point-in-time quote, and cross-sheet `SUMIF` renders as `#ERROR!` in some Excel
previews.

---

## 4. Use it on your own data

Same prompt, your file. The skill handles three input shapes:

### Target list — already has Azure SKUs

Any sheet with a column like `Azure VM SKU`, `VM Type at Target` or
`SKU Recommendation`. Headers are fuzzy-matched, so they don't need to match
exactly.

### Source hardware — current kit, no SKUs

Columns like `Total CPU`, `Total RAM GB`, and ideally utilisation. The skill
recommends SKUs, and will ask you the single most important question first:

> **Lift-and-shift, or right-size?**

Real example: a server provisioned with 72 CPU / 755 GB RAM but peaking at
150 GB needs `M128s v2` lifted-and-shifted, versus `E32s v5` right-sized —
roughly a **4x cost difference**.

Right-sizing uses observed peak × 1.3 by default, and suggests a cheaper
alternative wherever one size down still clears peak with 20% headroom.

### A typed requirement — no inventory at all

AI, analytics and security workloads are sized by throughput, not server count:

> Price Microsoft Sentinel at 50 GB/day with 90-day retention, and an Azure
> OpenAI workload at 5M tokens/day.

The skill asks for the specific drivers each service needs. It won't invent them.

---

## 5. Things worth knowing

**Microsoft Fabric needs sizing first.** Fabric capacity is decided by workload
mix, not data volume, so the F SKU comes from the
[Fabric SKU Estimator](https://estimator.fabric.microsoft.com/) before the
calculator can price it. The skill drives both — see
[`reference/fabric-sizing.md`](azure-boq-creator-skill/reference/fabric-sizing.md).

**Some services aren't priceable here at all.** M365 Copilot, Copilot Studio,
Azure Sphere, Stack Hub and Information Protection are licensed elsewhere. The
skill states them as excluded rather than dropping them silently.

**Several services have been renamed.** Searching "Azure AI Search" or
"Cognitive Services" returns nothing — they're now `Foundry IQ` and
`Foundry Tools`. See
[`reference/service-catalogue.md`](azure-boq-creator-skill/reference/service-catalogue.md)
for 90+ verified names.

**What the estimate is not.** Calculator list pricing. It excludes VAT,
customer-specific agreement discounts, support plans, and anything outside the
scope you agreed. Always confirm the inferred values before it reaches a
customer.

---

## 6. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Skill doesn't trigger | Skills load at session start — open a **new** session |
| `No server rows found` | The workbook has no SKU column. That's the routing signal for source-hardware mode, not a failure |
| `openpyxl` not found | `pip install openpyxl` |
| A calculator row wedges mid-build | Known behaviour after heavy reconfiguration. The skill clones a healthy row and deletes the stuck one |
| A product isn't found by name | It's probably been renamed — check `service-catalogue.md`, or use `__findProducts()` to re-derive it |

---

## 7. Going deeper

| Document | What's in it |
|---|---|
| [`SKILL.md`](azure-boq-creator-skill/SKILL.md) | the workflow the skill follows |
| [`reference/calculator-dom.md`](azure-boq-creator-skill/reference/calculator-dom.md) | selectors and 13 failure modes found building real estimates |
| [`reference/products.md`](azure-boq-creator-skill/reference/products.md) | driving any non-VM product via runtime schema discovery |
| [`reference/service-catalogue.md`](azure-boq-creator-skill/reference/service-catalogue.md) | verified product names across all 13 Azure categories |
| [`reference/fabric-sizing.md`](azure-boq-creator-skill/reference/fabric-sizing.md) | the Fabric estimator → calculator round trip |
| [`tests/README.md`](tests/README.md) | what's tested, and what deliberately isn't |

Run the test suite any time:

```bash
python tests/run_tests.py     # 123 assertions, no network or browser
```
