# Non-VM products — how to price anything on the calculator

There are 222 products. **Do not hardcode them.** Every product renders the same
DOM shape — `select[name=…]`, `input[type=number][name=…]`, an optional region
select, optional `button.toggle-submodule-btn` sections — so discover the schema
at runtime and drive it generically.

## The loop

```js
await __addProduct('Azure SQL Database');       // search + click its Add card
const row = __rows()[__rows().length - 1];
await __expand(row);
__describeRow(row);                              // -> {selects, numbers, submodules, radios}
await __cfgGeneric(row, {
  selects: { region: 'qatar-central', purchaseModel: 'vcore', vcoreTier: 'general-purpose' },
  numbers: { singleCount: 2 },
  label:   'PDP | SQL MI PROD | GP 8 vCore',
});
```

`__describeRow` returns every field name **and its legal option values**, so you
never guess an enum. Feed what you learn straight back into `__cfgGeneric`.

**Discover → configure → re-discover.** Setting one field often reveals a
different set of fields (Bandwidth is the clearest case below). Do not assume the
schema you read first is the whole schema.

`__cfgGeneric` returns `{ok, applied, missed}`. **Always check `missed`** — see
failure mode 10 in `calculator-dom.md`, because missing fields usually mean the
region does not support the option you chose.

## Verified schemas

Captured live. Treat as a starting point and re-run `__describeRow` to confirm —
Azure changes these.

### Storage Accounts
```
selects  region, type, performanceTier, storageAccountType, fileStructure,
         accessTier, redundancy, storageUnits, blobDataRetrievalUnits
numbers  count, blobWriteOperations, blobCreateContainerOperations,
         blobReadOperations, blobOtherOperations, blobDataRetrieval,
         blobDataWrite, geoReplications
```
- `performanceTier` `premium|standard`
- `accessTier` `hot|cool|cold|archive`
- `redundancy` `lrs|zrs|grs|ra-grs|gzrs|ra-gzrs` — **not region-filtered, see failure mode 10**
- `storageUnits` `1` (GB) or `1024` (TB); `count` is the number of those units

### Azure SQL Database
```
selects  region, type, purchaseModel, vcoreTier, computeTier, generation,
         instanceSize, zoneRedundancy, databasePaymentOption, redundancy,
         singleHyperscaleReplicaHoursFactor, singleHyperscaleStorageUnitsFactor,
         ltrDatabaseSizeFactor
numbers  singleCount, singleHyperscaleStorageUnits, backupStorageSize,
         ltrDatabaseSize, weeklyBackups, monthlyBackups, yearlyBackups
```
Use `type` to switch between single database / elastic pool / managed instance.

### Azure Kubernetes Service (AKS)
```
selects  region, kubernetesServiceOfferTier, slaOptionValue, operatingSystem,
         category, hoursFactor, managedDiskTier, managedDiskType
numbers  clusterCount, count, hours, managedDisks
```
Node VMs are picked with the same `.instancesSearchDropdown__input` as Virtual
Machines, so `__pickInstance` works here too. Price the control plane
(`kubernetesServiceOfferTier`) separately from the node pool.

### App Service
```
selects     region, type, tier, size, hoursFactor
numbers     instances, hours
submodules  SSL Connections, Custom Domain and Certificates
```

### Azure Files
```
selects  region, performanceTier, redundancy, billingModel,
         provisionedV2StorageFactor, provisionedV2IopsHoursFactor, …
numbers  provisionedV2StorageUnits, provisionedV2Iops,
         provisionedV2Throughput, fileSyncV2Servers, …
```
Provisioned v2 bills storage, IOPS and throughput separately — set all three.

### Bandwidth
```
selects  dataTransferType  interregion | internetegress
```
No `region` select, and **the rest of the fields depend on `dataTransferType`** —
set it first, then re-run `__describeRow`:

| dataTransferType | then you get |
|---|---|
| `interregion` | `sourceRegion`, `destinationRegion`, number `interRegionUnits` |
| `internetegress` | `sourceRegion`, `routedVia`, number `internetEgressUnits` |

A good worked example of why you discover, configure, then re-discover. Add one
Bandwidth row per source→destination pair.

## Product names that need the search fallback

`__addProduct` tries the full name, then strips parentheses, then shortens.
Names with brackets fail on an exact search:

| Asked for | Search that works |
|---|---|
| `Azure Kubernetes Service (AKS)` | `Azure Kubernetes Service` |
| `Storage Accounts` | exact |
| `Azure SQL Database` | exact |
| `App Service` | exact |
| `Azure Files` | exact |
| `Bandwidth` | exact |

**For any other service, look the name up in `service-catalogue.md` first.**
Several products have been renamed (Azure AI Search → `Foundry IQ`, Cognitive
Services → `Foundry Tools`), and a handful are reachable only by typing their
name because the category tabs don't render them — `Virtual Machine Scale Sets`,
`Azure Dedicated Host`, `Azure Elastic SAN`, `Managed Disks`,
`Azure Container Storage`.

## Scoping a full-stack BoQ

A migration BoQ is rarely only VMs. Ask which of these are in scope, and say
plainly that anything excluded is excluded in the final report:

- **Compute** — Virtual Machines, AKS, App Service, Functions
- **Storage** — managed disks (inside each VM row), Storage Accounts, Azure Files, Backup
- **Database** — SQL Database / Managed Instance, PostgreSQL, MySQL, Cosmos DB
- **Network** — Bandwidth, Load Balancer, Application Gateway, VPN Gateway, ExpressRoute, Firewall, Public IPs
- **Platform** — Key Vault, Monitor / Log Analytics, Defender for Cloud, Site Recovery, Entra ID P1/P2

Cheap to add and almost always forgotten: **Bandwidth, Public IPs, Backup,
Log Analytics ingestion**. Egress in particular can be a large surprise.
