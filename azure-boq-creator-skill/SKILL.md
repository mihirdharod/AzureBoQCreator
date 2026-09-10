---
name: azure-boq-creator-skill
description: Build a priced Azure Bill of Quantities for any Azure service - compute, storage, databases, AI and machine learning, analytics and data platform, containers, networking, security, IoT, integration and management - from an inventory (Excel, CSV) or a typed requirement. Recommends and right-sizes VM SKUs from source hardware or utilisation data, drives the Azure Pricing Calculator in a browser canvas, verifies every line item, and exports an Excel BoQ with per-application and per-service-category cost summaries. Use whenever someone asks to price Azure infrastructure or services, build a BoQ, cost estimate or quote, size or right-size VMs and disks, estimate a migration, landing-zone, data platform or AI workload cost, or convert an inventory or requirement into Azure pricing.
---

# Azure BoQ Creator Skill

Build a priced Azure Bill of Quantities. The flow is:

**Scope → parse/size → confirm commercial assumptions → drive the calculator → verify → export → summarise.**

Works for **any of the calculator's ~220 products**, not just VMs — AI, analytics,
databases, containers, security, IoT and integration all price through the same
mechanism. The Azure Pricing Calculator has **no import API**, so the only
reliable way to build a large estimate is to drive its DOM in a browser canvas.
This skill contains the selectors, a tested harness, and the failure modes.

Read before writing any browser code:
- `reference/calculator-dom.md` — selectors, React quirks, 13 failure modes
- `reference/products.md` — how to price non-VM services generically
- `reference/service-catalogue.md` — verified product names for 90+ services
  across all 13 categories, plus what is **not** priceable on the calculator
- `reference/fabric-sizing.md` — Fabric is sized on a **separate** estimator
  before it can be priced; read this before quoting any Fabric workload

---

## 0. Scope the BoQ

Ask what's in scope before pricing anything. A BoQ is rarely only VMs, and
anything you leave out must be stated plainly in the final report.

| Category | Typical line items |
|---|---|
| **Compute** | Virtual Machines, VM Scale Sets, AKS, App Service, Functions, Container Apps, Batch, AVS, OpenShift, Virtual Desktop |
| **Storage** | managed disks (per VM), Storage Accounts (blob/archive/queue/table/ADLS), Azure Files, NetApp Files, Elastic SAN, Backup |
| **Databases** | SQL DB, SQL Managed Instance, Cosmos DB, PostgreSQL, MySQL, MariaDB, Cache for Redis, Cassandra |
| **AI + machine learning** | Azure OpenAI, Foundry Tools, Foundry IQ, Azure Machine Learning, Document Intelligence, AI Bot Service |
| **Analytics / data platform** | Microsoft Fabric, Synapse, Databricks, Data Factory, Stream Analytics, Data Explorer, HDInsight, Purview |
| **Containers** | Container Instances, Container Registry, Container Storage, AKS, OpenShift |
| **Networking** | Bandwidth (egress), VNet, Load Balancer, App Gateway, VPN/ExpressRoute, Front Door, CDN, Firewall, Bastion, DNS, IP Addresses, Private Link |
| **Security** | Microsoft Sentinel, Key Vault, Defender for Cloud, DDoS Protection, Dedicated HSM |
| **Management** | Azure Monitor / Log Analytics, Backup, Site Recovery, Automation, Policy, Advisor, Cost Management |
| **IoT** | IoT Hub, IoT Central, Digital Twins, IoT Edge |
| **Integration / web** | API Management, Service Bus, Event Grid, Event Hubs, Logic Apps, SignalR, Notification Hubs |
| **Migration** | Azure Migrate, Database Migration Service, Data Box |
| **Identity / hybrid** | Entra ID, Entra External ID, Azure Arc, Stack Edge |

Cheap and almost always forgotten: **Bandwidth (egress), Public IPs, Backup,
Log Analytics ingestion**. Egress in particular can be a large surprise.

Data platform and AI BoQs have a different shape to a migration BoQ — cost is
driven by **throughput, tokens, ingestion volume and capacity units** rather than
server count. Ask for those volumes explicitly; there's no inventory to read them
from.

If the inventory is only servers, say so and offer to add the rest — don't
silently produce a VM-only BoQ and call it a full estimate.


---

## 1. Parse the input

Inputs come in three shapes. Check which one you have **before** parsing:

| Shape | Tell-tale | How to handle |
|---|---|---|
| **Target list** — already has Azure SKUs | a column like `Azure VM SKU`, `VM Type at Target`, `SKU Recommendation` | `parse_inventory.py` |
| **Source hardware** — current kit, no SKUs | `Total CPU`, `Total RAM GB`, `Physical or VM`, often `… Utilization` columns | `size_from_source.py` |
| **Typed requirement** — no inventory at all | "price a Fabric F64 with 2 TB OneLake", "an OpenAI workload at 5M tokens/day" | go straight to §1c |

Both scripts are for **server** inventories. AI, analytics, security and
integration workloads usually have no server list — they are sized by capacity
and throughput, so they follow §1c.

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

### 1c. Non-server workloads (AI, data, security, integration)

There is nothing to parse — the cost drivers are volumes the user has to supply.
Look the product up in `service-catalogue.md`, add it, then run `__describeRow`
to see exactly which quantities it wants, and **ask for those specific numbers
rather than guessing**. Typical drivers:

| Workload | Ask for |
|---|---|
| Azure OpenAI | model, tokens/month in and out, PTU vs pay-as-you-go |
| Foundry Tools / AI services | transactions or records per month, per feature |
| **Microsoft Fabric** | **size it on the Fabric SKU Estimator first — see `reference/fabric-sizing.md`** |
| Databricks / Synapse | DBU or vCore hours per month, tier |
| Data Factory | pipeline activity runs, data movement hours |
| Cosmos DB | RU/s (or serverless RU/month), stored GB, multi-region |
| Event Hubs / Service Bus | throughput units, messages/month |
| Microsoft Sentinel / Monitor | **GB ingested per day** and retention months |
| Defender for Cloud | resource counts per plan (servers, SQL, storage) |
| API Management | tier and units |
| Container Registry | tier, storage GB |

Two of these are routinely underestimated and worth flagging: **Sentinel/Log
Analytics ingestion** (priced per GB/day, and it compounds with retention) and
**Cosmos DB RU/s** provisioned versus actually used.

### Services sized by a separate tool

Some services cannot be sized from a requirement at all — you size them in a
dedicated estimator, then price the answer on the calculator:

| Service | Size it here | Then price |
|---|---|---|
| Microsoft Fabric | `https://estimator.fabric.microsoft.com/` | `Microsoft Fabric` product, `computeSku` |
| Azure VMware Solution | Azure Migrate AVS assessment | `Azure VMware Solution` |
| Cosmos DB | Cosmos capacity planner | `Azure Cosmos DB` |
| VMs from an existing estate | Azure Migrate, or `size_from_source.py` | `Virtual Machines` |

Never invent these numbers. If the user doesn't have them, price a clearly
labelled scenario ("assumes 50 GB/day ingestion") and say so in the report.

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
See `reference/products.md` for verified schemas, and
`reference/service-catalogue.md` for the exact product name to pass to
`__addProduct` — several services have been renamed (Azure AI Search is now
`Foundry IQ`, Cognitive Services is now `Foundry Tools`) and searching the old
name returns nothing.

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
