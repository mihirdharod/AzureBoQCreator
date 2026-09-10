---
name: azure-boq-creator-agent
description: Build a priced Azure Bill of Quantities for any Azure service - VMs, storage, databases, containers, networking - from a server/resource inventory (Excel, CSV) or a typed requirement. Recommends VM SKUs from source hardware or utilisation data, drives the Azure Pricing Calculator in a browser canvas, and exports an Excel BoQ with a per-application cost summary. Use whenever someone asks to price Azure infrastructure, build a BoQ, cost estimate or quote, size or right-size VMs and disks, estimate a migration or landing-zone cost, or convert an inventory into Azure pricing.
---

# Azure BoQ Creator Agent

Build a priced Azure Bill of Quantities. The flow is:

**Scope → parse/size → confirm commercial assumptions → drive the calculator → verify → export → summarise.**

Works for **any Azure service**, not just VMs. The Azure Pricing Calculator has
**no import API**, so the only reliable way to build a large estimate is to drive
its DOM in a browser canvas. This skill contains the selectors, a tested harness,
and the failure modes.

Read before writing any browser code:
- `reference/calculator-dom.md` — selectors, React quirks, 11 failure modes
- `reference/products.md` — how to price non-VM services generically

---

## 0. Scope the BoQ

Ask what's in scope before pricing anything. A migration BoQ is rarely only VMs,
and anything you leave out must be stated plainly in the final report.

- **Compute** — Virtual Machines, AKS, App Service, Functions
- **Storage** — managed disks (per VM), Storage Accounts, Azure Files, Backup
- **Database** — SQL DB / Managed Instance, PostgreSQL, MySQL, Cosmos DB
- **Network** — Bandwidth, Load Balancer, App Gateway, VPN/ExpressRoute, Firewall, Public IPs
- **Platform** — Key Vault, Monitor / Log Analytics, Defender, Site Recovery

Cheap and almost always forgotten: **Bandwidth (egress), Public IPs, Backup,
Log Analytics ingestion**.

If the inventory is only servers, say so and offer to add the rest — don't
silently produce a VM-only BoQ and call it a full estimate.


---

## 1. Parse the inventory

Inventories come in two shapes. Check which one you have **before** parsing:

| Shape | Tell-tale | Script |
|---|---|---|
| **Target list** — already has Azure SKUs | a column like `Azure VM SKU`, `VM Type at Target`, `SKU Recommendation` | `parse_inventory.py` |
| **Source hardware** — current kit, no SKUs | `Total CPU`, `Total RAM GB`, `Physical or VM`, often `… Utilization` columns | `size_from_source.py` |

`parse_inventory.py` exits with "No server rows found" when there's no SKU
column — that's the signal to switch to `size_from_source.py`, not a bug.

### 1a. Target list

```powershell
python scripts/parse_inventory.py "ServerList.xlsx" --out inventory.csv --exclude ECP "SQL PAAS"
```

Fuzzy-matches column headers, so it copes with sheets that each name things
differently. It reports what it inferred — **review that before continuing**.

### 1b. Source hardware (recommend SKUs)

```powershell
python scripts/size_from_source.py "UAT sizing.xlsx" --mode rightsize --headroom 0.3 --region qatar-central
```

**Ask lift-vs-rightsize first — it is the single biggest cost lever**, often 3–4x.
A real example: a server with 72 CPU / 755 GB provisioned but 150 GB peak needs
`M128s v2` lift-and-shift versus `E32s v5` right-sized.

- `--mode rightsize` sizes to observed peak × (1 + headroom). Needs utilisation columns.
- `--mode lift` sizes to provisioned specs. Use when there's no utilisation data,
  or the workload is latency-critical and the customer wants no risk.

It picks the cheapest series that fits (F → D → E → M), prints a **cheaper
alternative** column where one size down still clears peak with ≥20% headroom,
and writes `plan.json` ready for the harness. Azure sizes double each step, so
a +30% target frequently lands just over a boundary — show the user the table
and the alternatives and let them decide.

Note it also warns when it picks F-series, which has **no Reserved Instance**.

### Then confirm these four things

| Question | How to resolve |
|---|---|
| Which sheets are in scope? | List sheets + row counts, ask which to exclude. Container/PaaS sheets (OpenShift, SQL MI) usually price separately — flag them. |
| Region(s)? | Look for a region in sheet names or cells. Confirm — never assume. |
| Pricing term? | **Ask.** Biggest cost lever. Offer: 3-yr RI for PROD + PAYG non-PROD / all PAYG / all 3-yr RI / savings plan. |
| Azure Hybrid Benefit? | **Ask** if any Windows VMs. Swings Windows cost ~40%. |

Inference rules the parser applies (state them back to the user):

- **OS** — from an OS column; else server naming (`...W...` → Windows, `...L...` → Linux); else Windows.
- **PROD** — env is `PROD`/`Production`. Everything else (QA/DEV/CFG/Test/UAT) is non-PROD.
- **Storage `?` or blank** — inherits the **median of peer servers in the same application**, never a global default. Report every inferred row so the user can correct it.
- **Disk type** — from the sheet if stated; else Premium SSD for PROD, Standard SSD for non-PROD.

If the whole inventory is UAT/staging that mirrors production, flag the
Standard SSD default — performance testing usually wants Premium SSD.

### Line-item granularity

Ask, or infer from how the user will use it:

- **One row per server** (default for a BoQ) — traceable, and how customers want to review it. Name each row `<Application> | <ServerName> | <SKU> | <DiskType> ~<size>GB`.
- **Grouped by SKU** — fewer rows, faster to build, fine for a ballpark.

Per-server is strongly preferred for anything customer-facing. 95 rows takes
roughly 15 minutes of driver time — set that expectation up front.

---

## 2. Drive the calculator

Open the canvas and install the harness:

```
open_canvas  canvasId="browser"  instanceId="azure-calc"
             input={"url":"https://azure.microsoft.com/en-us/pricing/calculator/"}
```

The **`page_id` for every action is the `instanceId` you chose** (`azure-calc`).

Paste `scripts/harness.js` via `evaluate_javascript` to install helpers on
`window`, then drive it. The harness handles React state, product search, the
instance search quirks, expand/collapse, disks, and per-row verification.

> **Critical:** `evaluate_javascript` times out after ~5 seconds, but the page
> keeps running. Never `await` a long loop inside an eval. Start a
> fire-and-forget async driver that writes progress to `window.__stat`, then poll
> `__stat` in separate short calls. See `reference/calculator-dom.md`.

### Virtual Machines

Build order per row — **this order matters**:

1. `region` → 2. `operatingSystem` → 3. instance (search dropdown) →
4. `count` → 5. billing radio → 6. managed disk → 7. `displayName`

Region and OS reset downstream fields, so they go first. **Set billing after
region, always** — changing region silently reverts a reservation to pay-as-you-go.

Drive with `runPlan(plan)`.

### Any other service

Don't hardcode product schemas — discover them:

```js
await __addProduct('Azure SQL Database');
const row = __rows()[__rows().length - 1];
await __expand(row);
__describeRow(row);          // field names + legal option values
await __cfgGeneric(row, { selects:{...}, numbers:{...}, label:'...' });
```

`__cfgGeneric` applies one field at a time and retries, because field sets mutate
as you configure. **Always check its `missed` list** — missing fields usually mean
the region doesn't support the option you picked (failure mode 10), not a code bug.

Use `runMixedPlan(plan)` for a plan combining VM and non-VM items.
See `reference/products.md` for verified schemas.

---

## 3. Verify before reporting

Never report a total without an independent read-back. Re-read the DOM (or the
collapsed row summary text) and assert:

- row count == expected line items
- every row's SKU, count, region, disk tier, disk size, disk count match the plan
- no row unintentionally on `payg`
- `0 managed disks` appears nowhere

`__auditRows(plan)` does this for VM rows and returns a mismatch list. Report the
mismatch count explicitly — "verified, 0 mismatches" — and fix any before quoting.

### Also run `__auditCosts(targetRegion)` — always

A total can look perfectly reasonable while a line item is silently wrong.
`__auditCosts` catches the three failures that a total hides:

| Flag | Meaning |
|---|---|
| `ZERO_COST` | A line item priced $0.00. Almost always an unset quantity, or a quantity sitting inside a free tier. |
| `LABEL_QTY_NOT_IN_ROW` | The label says "5 TB" but the row isn't configured for it. **Labels are free text and are never validated against configuration.** |
| `REGION_MISMATCH` | A region field left at its default. Non-VM products have their own region selects — Bandwidth uses `sourceRegion` — that the main `region` never touches. |

**Quantities are entered in GB.** 5 TB is `5120`, not `5`. A real example from
testing: a Bandwidth row labelled "5 TB" was left at the default 5 GB in
us-west, priced **$0.00**, and hid **$602/month — 24% of the estimate**. The
total looked plausible, so nothing else would have caught it.

Some SKUs genuinely have **no Reserved Instance** (e.g. Fsv2). Fall back to the
3-year Savings Plan, and **tell the user which rows and why** — don't hide it.

---

## 4. Export and summarise

Click Export (`button.export-button`), then find the newest
`ExportedEstimate*.xlsx` in the user's Downloads folder.

```powershell
python scripts/build_summary.py "ExportedEstimate.xlsx" --out "Azure-BoQ-v1.0.xlsx"
```

This adds a formatted **Summary** sheet: KPI block, cost by application, by
region, by pricing model, and an assumptions note block. Application is the first
`|`-delimited segment of each line-item name.

Use **static values, not cross-sheet formulas** — `SUMIF` across sheets renders
as `#ERROR!` in the app's Excel preview canvas. A BoQ is a point-in-time quote,
so static is also more correct. Verify the summary total ties to the export total.

Open the result with `open_canvas canvasId="excel"` so the user can review it.

---

## 5. Report

Lead with the numbers, then the assumptions that could move them:

- Monthly / annual / 3-year totals, VM count
- Cost by application, largest first, with % share
- Flag concentration ("PDP is 48.5% of spend on 19 of 95 servers")
- List every assumption the user should validate: inferred storage, AHB status,
  excluded scope, SKUs that fell back to a savings plan

Always state what's **excluded** — VAT, bandwidth, backup, ExpressRoute,
migration services, and any skipped sheets.

If asked for a summary email, keep the caveats — sales teams need to know what's
soft before it reaches a customer.
