# Microsoft Fabric — sizing before pricing

Fabric is a two-tool workflow, and getting it wrong is the difference between a
credible BoQ and a nonsense one.

| Step | Tool | Produces |
|---|---|---|
| 1. Size | **Fabric SKU Estimator** — `https://estimator.fabric.microsoft.com/` | which F SKU, OneLake GB, Power BI licence count |
| 2. Price | Azure Pricing Calculator, `Microsoft Fabric` product | monthly / annual cost |

**Never guess the F SKU.** Capacity is driven by workload mix, not data volume —
a verified run below landed on F256 where Power BI alone accounted for 42% of the
capacity, which no amount of reasoning about data size would have predicted.

The public page (`microsoft.com/en-us/microsoft-fabric/capacity-estimator`)
embeds the estimator in a **cross-origin iframe**, so you cannot drive it from
there. Navigate straight to `https://estimator.fabric.microsoft.com/`.

---

## Step 1 — the estimator

Plain `input` elements, no React setter tricks needed beyond the usual
`__setNative`. Three always-visible inputs:

| Field | Meaning |
|---|---|
| `totalDataSize` | total **compressed** data size in GiB |
| `dailyEtlRuns` | number of daily batch cycles |
| `sourceTablesPerEtlRun` | tables across all data sources |

Then tick the workloads the customer will use. Each is a checkbox:

```
LakehouseSQLEndpointWorkloadInput   DataAgentWorkloadInput
DataFactoryWorkloadInput            DataScienceWorkloadInput
DataWarehouseWorkloadInput          FabricPlanWorkloadInput
SparkWorkloadInput                  PowerBIWorkloadInput
PowerBIEmbeddedWorkloadInput        EventstreamV3WorkloadInput
EventhouseWorkloadInput             DataActivatorWorkloadInput
SQLDatabaseWorkloadInput
```

**Ticking a workload reveals extra numeric inputs** — the form grows as you go,
so re-read it after each change rather than assuming a fixed field set. Observed:

| Revealed by | Field |
|---|---|
| Data Factory | `dailydfG2executionHours` |
| Power BI | `dailyPowerBIReportViews`, `dailyPowerBIReportCreators`, `modelSize` |

Then click `Calculate` (the only button on the page) and read the result text.

### Worked example — verified

Input: 2048 GiB compressed · 4 daily batch cycles · 250 tables ·
Data Factory + Data Warehouse + Spark + Power BI ·
6 DF Gen2 hours/day · 5000 report views/day · 25 report creators · 50 GB model

Output:

```
Estimated Viable SKU   F256
Data Factory (3%)  Data warehouse (11%)  Power BI (42%)
Spark Jobs (2%)    OneLake Operations (1%)   Unused (42%)
Storage    OneLake: 3686.4 Gb
Licenses   Power BI Pro: 25
```

Three things to carry forward, not one:

1. **The F SKU** → priced on the Azure calculator.
2. **OneLake storage GB** → a separate field on the same calculator row.
3. **Power BI Pro licences** → **not priceable on the Azure calculator.** These
   are per-user M365 licences. State them as a separate line in the BoQ with a
   note, rather than dropping them.

Also report the **Unused %**. At 42% unused, F128 may well suffice — that is a
halving of cost and exactly the conversation a customer wants to have.

---

## Step 2 — price it on the calculator

Product name: `Microsoft Fabric`.

| Field | Values |
|---|---|
| `region` | standard region list |
| `computeSku` | `two` `four` `eight` `sixteen` `thirtytwo` `sixtyfour` `onetwentyeight` `twofiftysix` `fiveonetwo` `onezerotwofour` `twozerofoureight` |
| `computeHoursFactor` | `1` (Hours) · `24` (Days) · `730` (Month) |
| `computeHours` | quantity, multiplied by the factor |
| `storage` + `storageType` | OneLake hot — `onelake-hot-storage` or `onelake-bcdr-hot-storage` |
| `coolStorage` / `coldStorage` / `cacheStorage` | with matching `*StorageType` selects |

SKU value names are spelled-out numbers, so **F256 → `twofiftysix`**:

| SKU | value | | SKU | value |
|---|---|---|---|---|
| F2 | `two` | | F128 | `onetwentyeight` |
| F4 | `four` | | F256 | `twofiftysix` |
| F8 | `eight` | | F512 | `fiveonetwo` |
| F16 | `sixteen` | | F1024 | `onezerotwofour` |
| F32 | `thirtytwo` | | F2048 | `twozerofoureight` |
| F64 | `sixtyfour` | | | |

### The trap: hours factor MULTIPLIES

`computeHours` × `computeHoursFactor` is the total. Setting factor = `730`
(Month) **and** hours = `730` means 730 months.

Verified, same configuration:

| computeHoursFactor | computeHours | Monthly |
|---|---|---|
| `730` (Month) | `730` | **$30,013,020** ← wrong by 730x |
| `1` (Hours) | `730` | **$41,308** ← correct |

For a month of continuous capacity use **factor `1` and hours `730`**, or factor
`730` and hours `1`. A $30M line item is obvious, but the same mistake at
factor=`24` (Days) would give a 24x error that looks plausible enough to ship.

`__auditCosts()` will not catch this — the row is neither zero-cost nor
region-mismatched. Sanity-check any Fabric row against roughly
**$150–170 per capacity unit per month** in most regions.

### Example row

```js
await __addProduct('Microsoft Fabric');
const row = __rows()[__rows().length - 1];
await __expand(row);
await __cfgGeneric(row, {
  selects: { region: 'qatar-central', computeSku: 'twofiftysix',
             computeHoursFactor: '1', storageType: 'onelake-hot-storage' },
  numbers: { computeHours: 730, storage: 3686 },
  label:   'Analytics | Fabric F256 | OneLake 3686 GB',
});
```

Verified result: **$41,307.95/month** in Qatar Central.

---

## Reporting Fabric in the BoQ

- Quote the SKU **and** the estimator inputs that produced it. "F256" alone is
  unauditable; "F256 from 2 TB compressed, 4 daily cycles, 250 tables, DF + DW +
  Spark + Power BI" can be challenged and refined.
- Include the **workload split and unused %** — it is the strongest argument for
  sizing down.
- List **Power BI licences separately** and mark them as M365 licensing, outside
  the Azure calculator.
- Note that the estimator is **preview** and Microsoft explicitly calls its
  output guidance, not a binding quote. Say so in the assumptions.
- Reserved capacity for Fabric is bought separately from the pay-as-you-go rate
  priced here; if the customer will commit, flag that a further discount applies.

## Other services that size elsewhere

Fabric is not unique. When a service is sized by a dedicated tool, size there and
price on the calculator:

| Service | Sizing tool |
|---|---|
| Microsoft Fabric | Fabric SKU Estimator (above) |
| Power BI Embedded | Fabric / Power BI capacity guidance |
| Azure VMware Solution | AVS assessment in Azure Migrate |
| Virtual Machines from an existing estate | Azure Migrate assessment, or `size_from_source.py` |
| Cosmos DB | Cosmos capacity planner (RU/s) |
| Azure OpenAI | tokens/month; PTU calculator for provisioned throughput |
