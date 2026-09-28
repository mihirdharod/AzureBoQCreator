# Azure BoQ Creator Skill

[![tests](https://github.com/mihirdharod/AzureBoQCreator/actions/workflows/tests.yml/badge.svg)](https://github.com/mihirdharod/AzureBoQCreator/actions/workflows/tests.yml)

**From server list to signed-off BoQ.**

Turns a server inventory or a typed requirement into a priced Azure Bill of
Quantities — across any Azure service, not just VMs. Right-sizes VMs from
utilisation data, drives the Azure Pricing Calculator, **audits every line before
quoting**, and exports a client-ready Excel BoQ.

A **skill** for the GitHub Copilot app. No model, runtime or endpoint of its own —
it extends Copilot rather than running as a standalone service.

**[Tutorial](TUTORIAL.md)** · **[Impact model](IMPACT.md)** · **[Worked example](examples/)**

---

## Who this is for

| Role | What they get |
|---|---|
| **Solution Engineers / CSAs** | The afternoon back. Own the number without owning the clicking. |
| **Account Executives** | A credible figure from whatever the customer sent, without needing to know what an `FX64ms v2` is. |
| **Specialist Sellers** | Comparative scenarios — committed vs PAYG, with vs without Hybrid Benefit — in minutes instead of a re-do. |
| **CSU / Customer Success** | Consumption estimation broken down by application, region and service. |

The primary user is the **person who owns the number on a migration or
landing-zone deal**. Today that is almost always an SE or CSA, and almost always
under time pressure.

---

## The pain, concretely

Pricing an Azure estate by hand means building it in the Azure Pricing Calculator
one row at a time. Per server: add the row, set region, set OS, search the VM
size, pick it, set the count, choose the pricing term, expand managed disks, pick
a family, pick a size, set quantity, name the row.

**That is ~20 interactions per VM.** Counted from the fields the skill's own
harness has to set — not estimated.

| Estate | Interactions | Time (at 4s each) |
|---|---:|---:|
| 25 VMs | ~500 | ~33 min |
| 50 VMs | ~1,000 | ~1 hr |
| **95 VMs** | **~1,900** | **~2 hrs** |
| 200 VMs | ~4,000 | ~4.5 hrs |

And that is **one pass**, assuming no mistakes. Customers then ask "what does this
look like pay-as-you-go?" or "what if we only commit on production?" — and each of
those is every row again.

### The second pain: errors that survive a plausible total

This is the one that actually costs money. The calculator has failure modes that
produce **a wrong number rather than an error**:

- Changing region **silently reverts a reservation to pay-as-you-go**
- Fsv2 VMs have **no Reserved Instance at all** — a naive tool prices them at full rate
- Unsupported region/redundancy pairs **delete the pricing fields** instead of erroring
- Quantities are in **GB** — a row labelled "5 TB" left at the default 5 GB prices at **$0.00**, because the first 100 GB of egress is free
- The hours factor **multiplies** — "Month" × 730 hours means 730 months
- On a signed-in saved estimate, **Export returns the server copy**, not your unsaved edits

Each of these was found building real estimates. **14 are documented.**

A real one: a bandwidth line labelled "5 TB" was sitting at the default 5 GB in
the wrong region, pricing at **$0.00**. That was **$602/month — 24% of the
estimate** — invisible inside a total that looked entirely sensible.

---

## What success looks like

Measurable, and checkable against this repo:

| Success criterion | Target | Status |
|---|---|---|
| A 95-VM BoQ is produced without manual calculator work | < 20 min, largely unattended | ✅ measured |
| Re-pricing a scenario does not mean rebuilding | Same estate, new term, no re-entry | ✅ 95/95 rows converted, 0 errors |
| No line item reaches a customer unverified | 0 unflagged zero-cost / mismatched / default-region rows | ✅ audit runs before every quote |
| Every assumption is visible | Inferred storage, OS and disk type reported per row | ✅ in output |
| A peer can adopt it without help | Copy a folder, no server, no credentials | ✅ see [TUTORIAL.md](TUTORIAL.md) |
| Coverage is not VM-only | All 13 Azure service categories | ✅ 90+ verified product names |

**Not success:** replacing judgement. This produces calculator list pricing — a
first draft you review, not a quote you forward.

---

## Impact

Full model and assumptions in **[IMPACT.md](IMPACT.md)**. Headline:

| Estate | Scenarios | Manual | With skill | Saved |
|---|---:|---:|---:|---:|
| 50 VMs | 1 | ~67 min | ~11 min | **~56 min** |
| 95 VMs | 1 | ~127 min | ~16 min | **~111 min** |
| 95 VMs | 3 | ~380 min | ~48 min | **~5.5 hrs** |
| 200 VMs | 3 | ~800 min | ~85 min | **~12 hrs** |

Most of the skill's time is **unattended** — the driver runs while you do
something else. The manual figure is all keyboard time.

**Frequency:** this is not an edge case. Every migration assessment, every
landing-zone proposal, every modernisation business case needs a BoQ, and each
one is typically re-priced two to four times as the commercial shape changes.

At **10 BoQs a year** on a 95-VM estate with 3 scenarios each, the model returns
roughly **55 hours** per person.

**The error avoidance is the harder-to-price half.** A single missed line at 24%
of an estimate is not a time saving — it is a credibility event with a customer.

---

## The reusable pattern

The transferable idea is **not** "automate the Azure calculator".

> **When a tool has no API, drive its UI by discovering its schema at runtime —
> then verify the result independently, because a UI that cannot error will
> happily give you a wrong number.**

Three parts, each reusable on its own:

**1. Runtime schema discovery instead of hardcoding.** The calculator has ~220
products. `__describeRow()` reads any product's fields *and their legal values*
at runtime, and `__cfgGeneric()` applies them one at a time, re-querying between
changes because field sets mutate. The result: it prices services the author
never tested, and survives Microsoft's renames. **Transfers to any complex web
form** — other cloud calculators, internal quoting tools, licensing portals.

**2. Inference that is always visible.** Where the input is ambiguous, infer from
*peers in the same group* rather than a global default, and report every
inference. **Transfers to any messy-spreadsheet ingestion problem.**

**3. Verify before you trust.** `__auditCosts()` re-reads the result and checks
for zero-cost rows, labels that don't match configuration, and fields left at
defaults. **Transfers to any automation whose output a human will sign.**

The documented failure modes in
[`calculator-dom.md`](azure-boq-creator-skill/reference/calculator-dom.md) are
themselves reusable: anyone automating the Azure calculator — in any language,
with any framework — will hit the same 14 traps.

---

## Adopt it

Deliberately low friction. **Installation is copying a folder.**

- ❌ No MCP server to host
- ❌ No connector to configure
- ❌ No credentials — the Azure Pricing Calculator and Fabric SKU Estimator are both public
- ❌ No Azure subscription needed to produce an estimate
- ✅ One dependency: Python with `openpyxl`

**Windows**
```powershell
git clone https://github.com/mihirdharod/AzureBoQCreator.git
cd AzureBoQCreator
Copy-Item -Recurse .\azure-boq-creator-skill "$env:APPDATA\com.github.githubapp\app-skills\"
pip install openpyxl
```

**macOS / Linux**
```bash
git clone https://github.com/mihirdharod/AzureBoQCreator.git
cd AzureBoQCreator
cp -r ./azure-boq-creator-skill ~/Library/Application\ Support/com.github.githubapp/app-skills/
pip install openpyxl
```

Start a new session. A **worked example inventory ships with the repo**, so a new
adopter can do a full run before touching customer data.

---

## Documentation

| Document | For |
|---|---|
| **[TUTORIAL.md](TUTORIAL.md)** | Install → first BoQ, step by step, with a worked example |
| **[IMPACT.md](IMPACT.md)** | The time model, its assumptions, and how to re-run it for your own numbers |
| [`SKILL.md`](azure-boq-creator-skill/SKILL.md) | The workflow the skill follows |
| [`reference/calculator-dom.md`](azure-boq-creator-skill/reference/calculator-dom.md) | Selectors and **14 documented failure modes** |
| [`reference/products.md`](azure-boq-creator-skill/reference/products.md) | Driving any non-VM product via runtime schema discovery |
| [`reference/service-catalogue.md`](azure-boq-creator-skill/reference/service-catalogue.md) | **90+ verified product names** across 13 categories, plus what can't be priced |
| [`reference/fabric-sizing.md`](azure-boq-creator-skill/reference/fabric-sizing.md) | The Fabric estimator → calculator round trip |
| [`examples/`](examples/) | Fictional inventory, safe to demo and share |
| [`tests/README.md`](tests/README.md) | What's tested, and what deliberately isn't |

---

## What it covers

All 13 Azure service categories. Every product name verified against the live
calculator:

| Category | Examples |
|---|---|
| **Compute** | Virtual Machines, VM Scale Sets, AKS, App Service, Functions, Container Apps, Batch, AVS, OpenShift, Virtual Desktop |
| **Storage** | Managed Disks, Storage Accounts (blob / archive / queue / table / ADLS Gen2), Azure Files, NetApp Files, Elastic SAN |
| **Databases** | SQL Database, SQL Managed Instance, Cosmos DB, PostgreSQL, MySQL, MariaDB, Cache for Redis, Cassandra |
| **AI + machine learning** | Azure OpenAI, Foundry Tools, Foundry IQ, Azure Machine Learning, Document Intelligence, AI Bot Service |
| **Analytics** | Microsoft Fabric, Synapse, Databricks, Data Factory, Stream Analytics, Data Explorer, HDInsight, Purview |
| **Containers** | Container Instances, Container Registry, Container Storage |
| **Networking** | Bandwidth, VNet, Load Balancer, Application Gateway, VPN / ExpressRoute, Front Door, CDN, Firewall, Bastion, DNS, Private Link |
| **Security** | Microsoft Sentinel, Key Vault, Defender for Cloud, DDoS Protection, Dedicated HSM |
| **Management** | Azure Monitor, Backup, Site Recovery, Automation, Policy, Advisor, Cost Management |
| **IoT** | IoT Hub, IoT Central, Digital Twins, IoT Edge |
| **Integration** | API Management, Service Bus, Event Grid, Event Hubs, Logic Apps, SignalR |
| **Migration** | Azure Migrate, Database Migration Service, Data Box |
| **Identity + hybrid** | Entra ID, Entra External ID, Azure Arc, Stack Edge |

It also documents what **cannot** be priced on the calculator — M365 Copilot,
Copilot Studio, Azure Sphere, Stack Hub, Blueprints, Information Protection,
standalone WAF — so a BoQ declares them rather than dropping them silently.

**Names drift.** Searching "Azure AI Search" or "Cognitive Services" returns
**zero** results — they are now `Foundry IQ` and `Foundry Tools`. Five more
products are reachable only by typing their name, because the category tabs never
render them. The catalogue records all of it.

---

## What it does

1. **Reads the input** — detects whether a workbook already has Azure SKUs (a
   target list), is raw source hardware needing sizing, or whether there is no
   inventory at all and the workload is sized by capacity and throughput.
2. **Sizes the VMs** — for source hardware, recommends SKUs from CPU/RAM using
   observed peak utilisation. Suggests a cheaper alternative wherever one size
   down still clears peak with headroom.
3. **Asks the commercial questions** — lift-and-shift vs right-size, pricing term,
   Azure Hybrid Benefit, region. These move cost more than anything else, so they
   are never assumed. For AI and data workloads it asks for the real drivers —
   tokens/month, GB/day ingested, RU/s, capacity SKU.
4. **Builds the estimate** — drives the calculator, discovering each product's
   schema at runtime.
5. **Verifies** — flags zero-cost items, labels that don't match configuration,
   and region fields left at defaults.
6. **Exports** — Excel BoQ with cost by application, service category, region and
   pricing model.

---

## Use

Follow the [tutorial](TUTORIAL.md) for a full walkthrough. In short — attach a
server list and ask:

> Build me an Azure BoQ from this server list, priced in West Europe.

Or describe a workload with no inventory at all:

> Price a Microsoft Fabric F64 with 2 TB OneLake, Sentinel at 50 GB/day,
> and an Azure OpenAI workload at 5M tokens/day.

---

## Sizing happens before pricing

Some services can't be sized from a requirement — you size them in a dedicated
tool and price the answer on the calculator. **Microsoft Fabric** is the clearest
case, and [`reference/fabric-sizing.md`](azure-boq-creator-skill/reference/fabric-sizing.md)
documents the full round trip:

1. Drive the [Fabric SKU Estimator](https://estimator.fabric.microsoft.com/) with
   compressed data size, daily batch cycles, table count and workloads in use.
2. It returns an **F SKU**, a **OneLake storage figure**, and a **Power BI licence
   count** — three separate BoQ lines, only two of which the Azure calculator prices.
3. Price the F SKU and OneLake GB on the `Microsoft Fabric` product.

Verified: 2 TB compressed, 4 daily cycles, 250 tables, Data Factory + Warehouse +
Spark + Power BI → **F256**, OneLake 3,686 GB, 25 Power BI Pro licences →
**$41,308/month** in Qatar Central.

That run also reported **42% unused capacity** — the strongest argument for
dropping to F128 and halving the cost. The skill surfaces it rather than quietly
quoting the recommendation.

---

## Layout

```
azure-boq-creator-skill/
├── SKILL.md                     workflow the skill follows
├── reference/
│   ├── calculator-dom.md        selectors, React quirks, 14 failure modes
│   ├── products.md              how to drive any non-VM product
│   ├── service-catalogue.md     verified names for 90+ services
│   └── fabric-sizing.md         Fabric: size on the estimator, then price
└── scripts/
    ├── parse_inventory.py       target list  → normalised CSV
    ├── size_from_source.py      source hardware → SKU recommendations
    ├── harness.js               browser driver for the calculator
    └── build_summary.py         exported estimate → Excel summary sheet

TUTORIAL.md                      install → first BoQ, step by step
IMPACT.md                        time model and assumptions
examples/                        worked example inventory (fictional)
tests/
├── run_tests.py                 131 assertions, no network or browser
├── make_fixtures.py             regenerates the synthetic fixtures
└── fixtures/                    synthetic workbooks, no customer data
```

---

## Design notes

**Schema discovery over hardcoding.** The calculator has ~220 products but they
all share one DOM shape — only field names differ. Rather than encode each
product, the harness reads a row's schema at runtime (`__describeRow` returns
field names *and* their legal option values) and configures it generically.

**Names drift, so they were verified.**
[`service-catalogue.md`](azure-boq-creator-skill/reference/service-catalogue.md)
was built by querying the live calculator, which surfaced two traps: renamed
services that return zero results, and five products reachable only by search.

**Verification is the point.** Automating the clicking is the easy half.
[`calculator-dom.md`](azure-boq-creator-skill/reference/calculator-dom.md)
documents 14 failure modes found building real estimates, several of which
produce a wrong number rather than an error.

**Ask, don't assume.** Lift-and-shift versus right-sizing changed one pair of
servers from `M128s v2` (128 vCPU / 2 TB RAM) to `E32s v5` — roughly a **4x cost
difference**. The skill surfaces that choice rather than picking one.

---

## Validation

```bash
pip install openpyxl
python tests/run_tests.py     # 131 assertions, no network, no browser
```

The suite covers the three Python scripts against synthetic fixtures, checks the
harness exports its full API and still contains its documented guards, verifies
the docs are internally consistent, and scans the repo for customer data. Several
assertions are regression guards for specific bugs found while building real
estimates, so a fix cannot silently be undone. See [`tests/README.md`](tests/README.md)
for what is deliberately **not** covered and why.

Built and verified against real inventories (not included here — the fixtures are
synthetic):

| Input | Result |
|---|---|
| 9 sheets, 95 VMs across 9 applications | $113,921/mo · $1.37M/yr — built, verified, exported |
| 3 sheets, 10 physical servers with utilisation data | Right-sized 608 → 536 vCPU, 2,038 → 1,456 GB RAM |
| Mixed VM + Storage + Files + SQL + Bandwidth | All 5 services priced and summarised |
| Fabric workload, no inventory | Estimator → F256 → $41,308/mo priced on the calculator |
| 95-row re-price from 3-yr RI to pay-as-you-go | 95/95 converted, disks intact, **zero errors**, unattended |

That last row moved the same estate from $113,921 to **$212,146/month — an 86%
increase**. Producing both versions credibly, and showing the delta, is often the
conversation that actually needs having.

---

## Notes

Prices are estimates from the public Azure Pricing Calculator and exclude VAT,
customer-specific agreement discounts, support plans, professional services, and
anything outside the agreed scope.

Always confirm inferred values — storage sizes, OS, environment — before a BoQ
goes to a customer.

The Fabric SKU Estimator is a **preview** tool, and Microsoft explicitly calls its
output guidance rather than a binding quote.

**It is a first draft you review, not a quote you forward.**
