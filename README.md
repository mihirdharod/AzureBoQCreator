# Azure BoQ Creator Agent

Converts an inventory or a typed requirement into a priced Azure Bill of
Quantities — across **any** Azure service, not just VMs. Right-sizes virtual
machines from utilisation data, prices compute, storage, databases, AI,
analytics, containers, networking and security on the Azure Pricing Calculator,
verifies every line item, and exports a client-ready Excel BoQ with
per-application and per-service-category cost summaries.

A skill for the **GitHub Copilot app**.

---

## Why

Building a BoQ by hand means opening the Azure Pricing Calculator and clicking
through one row per resource. For 95 servers that is a long afternoon, and the
errors it produces are the dangerous kind — a line item silently priced at $0.00
looks fine inside a plausible-looking total.

This skill automates the mechanical part and, more importantly, **audits the
result** for the failures a total hides.

## What it covers

All 13 Azure service categories. Every product name below was verified against
the live calculator (see `reference/service-catalogue.md`):

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

It also documents what **cannot** be priced on the calculator — Azure Sphere,
Stack Hub, Blueprints, Information Protection, standalone WAF — so a BoQ declares
them rather than dropping them silently.

## What it does

1. **Reads the input** — detects whether a workbook already has Azure SKUs
   (a target list), is raw source hardware, or whether there is no inventory at
   all and the workload is sized by capacity and throughput instead.
2. **Sizes the VMs** — for source hardware, recommends SKUs from CPU/RAM, using
   observed peak utilisation where available. Suggests a cheaper alternative
   wherever one size down still clears peak with headroom.
3. **Asks the commercial questions** — lift-and-shift vs right-size, pricing
   term, Azure Hybrid Benefit, region. These move cost more than anything else,
   so they are never assumed. For AI and data workloads it asks for the real
   drivers — tokens/month, GB/day ingested, RU/s, capacity SKU.
4. **Builds the estimate** — drives the Azure Pricing Calculator in a browser
   canvas, discovering each product's schema at runtime.
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

Or describe a workload with no inventory at all:

> Price a Microsoft Fabric F64 with 2 TB OneLake, Sentinel at 50 GB/day,
> and an Azure OpenAI workload at 5M tokens/day.

The skill will confirm scope and commercial assumptions, then build, verify and
export the estimate.

## Layout

```
azure-boq-creator-agent/
├── SKILL.md                     workflow the agent follows
├── reference/
│   ├── calculator-dom.md        selectors, React quirks, 13 failure modes
│   ├── products.md              how to drive any non-VM product
│   ├── service-catalogue.md     verified names for 90+ services
│   └── fabric-sizing.md         Fabric: size on the estimator, then price
└── scripts/
    ├── parse_inventory.py       target list  → normalised CSV
    ├── size_from_source.py      source hardware → SKU recommendations
    ├── harness.js               browser driver for the calculator
    └── build_summary.py         exported estimate → Excel summary sheet
```

## Sizing happens before pricing

Some services can't be sized from a requirement — you size them in a dedicated
tool and price the answer on the calculator. **Microsoft Fabric** is the clearest
case, and `reference/fabric-sizing.md` documents the full round trip:

1. Drive the [Fabric SKU Estimator](https://estimator.fabric.microsoft.com/) with
   compressed data size, daily batch cycles, table count and the workloads in use.
2. It returns an **F SKU**, a **OneLake storage figure**, and a **Power BI licence
   count** — three separate BoQ lines, only two of which the Azure calculator prices.
3. Price the F SKU and OneLake GB on the `Microsoft Fabric` product.

A verified run: 2 TB compressed, 4 daily cycles, 250 tables, Data Factory +
Warehouse + Spark + Power BI → **F256**, OneLake 3,686 GB, 25 Power BI Pro
licences → **$41,308/month** in Qatar Central.

Worth noting from that run: Power BI drove **42%** of the capacity and another
**42% was unused** — neither is predictable from data volume, which is exactly
why the SKU shouldn't be guessed.

## Design notes

**Schema discovery over hardcoding.** The calculator has ~220 products but they
all share one DOM shape — only field names differ. Rather than encode each
product, the harness reads a row's schema at runtime (`__describeRow` returns
field names *and* their legal option values) and configures it generically. That
means it handles services the author never tested.

**Names drift, so they were verified.** `reference/service-catalogue.md` was
built by querying the live calculator, which surfaced two traps: Azure AI Search
and Cognitive Services return **zero** results because they are now `Foundry IQ`
and `Foundry Tools`; and five products — Virtual Machine Scale Sets, Dedicated
Host, Elastic SAN, Managed Disks, Container Storage — are reachable only by
typing their name, because the category tabs never render them.

**Verification is the point.** Automating the clicking is the easy half.
`reference/calculator-dom.md` documents 13 failure modes found by building real
estimates, including several that produce a wrong number rather than an error:

- Changing region silently reverts a reservation to pay-as-you-go.
- Some SKUs (Fsv2) have no Reserved Instance at all — the skill falls back to a
  Savings Plan and says so rather than quietly pricing full rate.
- Selecting a region/redundancy pair the region doesn't support removes the
  pricing fields instead of raising an error.
- Quantities are entered in **GB**: "5 TB" means 5120. Defaults like Bandwidth's
  5 GB from us-west price at $0.00 because of the free tier.
- `hoursFactor` **multiplies** the hours field. Factor "Month" with 730 hours
  means 730 months — a verified Fabric row priced at **$30,013,020/month**
  instead of $41,308.

The Bandwidth one was a real bug caught in testing — a row labelled "5 TB" was
contributing **$0/month** to an estimate where it should have been $602, or 24%
of the total. `__auditCosts()` now catches that class of error.

**Ask, don't assume.** Lift-and-shift versus right-sizing changed one pair of
servers from `M128s v2` (128 vCPU / 2 TB RAM) to `E32s v5` — roughly a 4x cost
difference. The skill surfaces that choice rather than picking one.

## Validation

| Inventory | Result |
|---|---|
| 9 sheets, 95 VMs across 9 applications | $113,921/mo · $1.37M/yr — built, verified, exported |
| 3 sheets, 10 physical servers with utilisation data | Right-sized 608 → 536 vCPU, 2,038 → 1,456 GB RAM |
| Mixed VM + Storage + Files + SQL + Bandwidth | All 5 services priced and summarised |
| Fabric workload, no inventory | Estimator → F256 → $41,308/mo priced on the calculator |

## Notes

Prices are estimates from the public Azure Pricing Calculator and exclude VAT,
customer-specific agreement discounts, and anything outside the agreed scope.
Always confirm inferred values — storage sizes, OS, environment — before a BoQ
goes to a customer.
