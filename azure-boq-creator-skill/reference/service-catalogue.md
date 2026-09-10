# Service catalogue — verified calculator product names

Every entry below was **verified live against the Azure Pricing Calculator**.
The `__addProduct(name)` helper searches by name, so using the exact name here
avoids the search-fallback path.

Two things this table exists to solve:

1. **Microsoft renames services.** "Azure AI Search" and "Cognitive Services"
   both return **zero** results — they are now `Foundry IQ` and `Foundry Tools`.
   Searching the old name silently finds nothing.
2. **Some products only appear via search.** The category tabs render 119
   products, but several more (`Virtual Machine Scale Sets`, `Azure Dedicated
   Host`, `Azure Elastic SAN`, `Managed Disks`, `Azure Container Storage`) are
   only reachable by typing their name. Never assume the tabs are the full list.

> Verify with `__describeRow()` after adding — this table gives you the product
> name, not its field schema. See `products.md` for how to drive a row.

---

## AI + machine learning

| Asked for | Calculator name | Note |
|---|---|---|
| Azure OpenAI Service | `Azure OpenAI` | |
| Azure AI Search / Cognitive Search | `Foundry IQ` | **renamed** — old names return nothing |
| Azure Machine Learning | `Azure Machine Learning` | |
| Azure AI Services (Vision, Speech, Language, Translator) | `Foundry Tools` | **renamed** — one product covers all of these |
| Azure Bot Service | `Azure AI Bot Service` | |
| Content Safety | `Foundry Tools` | priced inside Foundry Tools |
| Document Intelligence | `Azure Document Intelligence in Foundry Tools` | separate product |
| Content Understanding | `Azure Content Understanding in Foundry Tools` | |

## Analytics

| Asked for | Calculator name |
|---|---|
| Microsoft Fabric | `Microsoft Fabric` |
| Azure Synapse Analytics | `Azure Synapse Analytics` |
| Azure Databricks | `Azure Databricks` |
| Azure Data Factory | `Azure Data Factory` |
| Azure Stream Analytics | `Azure Stream Analytics` |
| Azure Data Explorer | `Azure Data Explorer` |
| HDInsight | `HDInsight` |
| Azure Analysis Services | `Azure Analysis Services` |
| Microsoft Purview | `Microsoft Purview` |

## Compute

| Asked for | Calculator name | Note |
|---|---|---|
| Virtual Machines | `Virtual Machines` | use `__cfgRow`, not `__cfgGeneric` |
| Virtual Machine Scale Sets | `Virtual Machine Scale Sets` | **search-only** |
| Azure Kubernetes Service | `Azure Kubernetes Service (AKS)` | search fallback strips the `(AKS)` |
| App Service | `App Service` | |
| Azure Functions | `Azure Functions` | |
| Azure Spring Apps | `Azure Spring Apps` | |
| Azure Container Apps | `Azure Container Apps` | |
| Batch | `Batch` | |
| Cloud Services | `Cloud Services` | |
| Dedicated Host | `Azure Dedicated Host` | **search-only** |
| Azure VMware Solution | `Azure VMware Solution` | |
| Azure Red Hat OpenShift | `Azure Red Hat OpenShift` | |
| Azure Virtual Desktop | `Azure Virtual Desktop` | |

## Databases

| Asked for | Calculator name | Note |
|---|---|---|
| Azure SQL Database | `Azure SQL Database` | |
| SQL Managed Instance | `Azure SQL Managed Instance` | |
| Azure Cosmos DB | `Azure Cosmos DB` | also covers the Gremlin/Table APIs |
| Azure Database for PostgreSQL | `Azure Database for PostgreSQL` | |
| Azure Database for MySQL | `Azure Database for MySQL` | |
| Azure Database for MariaDB | `Azure Database for MariaDB` | |
| Azure Cache for Redis | `Azure Cache for Redis` | see also `Azure Managed Redis` |
| Cassandra API | `Azure Managed Instance for Apache Cassandra` | |
| Table Storage | `Storage Accounts` | set `type` to table storage |

## Containers

| Asked for | Calculator name | Note |
|---|---|---|
| Azure Container Instances | `Azure Container Instances` | |
| Azure Container Registry | `Azure Container Registry` | |
| Azure Container Storage | `Azure Container Storage` | **search-only** |
| Red Hat OpenShift | `Azure Red Hat OpenShift` | |

## Hybrid + multicloud

| Asked for | Calculator name | Note |
|---|---|---|
| Azure Arc | `Azure Arc` | |
| Azure Stack Edge | `Azure Stack Edge` | |
| Azure Stack Hub | — | **not on the calculator** |
| Azure Stack HCI | `Azure Kubernetes Service on Azure Local` | closest equivalent |

## Internet of Things

| Asked for | Calculator name | Note |
|---|---|---|
| IoT Hub | `Azure IoT Hub` | |
| Azure Digital Twins | `Azure Digital Twins` | |
| IoT Central | `Azure IoT Central` | |
| Windows 10 IoT Core Services | `Windows 10 IoT Core Services` | |
| Azure IoT Edge | `Azure IoT Edge` | |
| Azure Sphere | — | **not on the calculator** |

## Management + governance

| Asked for | Calculator name | Note |
|---|---|---|
| Azure Monitor | `Azure Monitor` | Log Analytics ingestion priced here |
| Azure Advisor | `Azure Advisor` | |
| Azure Backup | `Azure Backup` | |
| Azure Site Recovery | `Azure Site Recovery` | |
| Azure Policy | `Azure Policy` | |
| Microsoft Cost Management | `Microsoft Cost Management` | |
| Azure Automation | `Automation` | no "Azure" prefix |
| Azure Blueprints | — | **not on the calculator** (deprecated) |

## Migration

| Asked for | Calculator name |
|---|---|
| Azure Migrate | `Azure Migrate` |
| Database Migration Service | `Azure Database Migration Service (classic)` |
| Azure Data Box | `Azure Data Box` |

## Networking

| Asked for | Calculator name | Note |
|---|---|---|
| Virtual Network | `Virtual Network` | |
| VPN Gateway | `VPN Gateway` | |
| ExpressRoute | `Azure ExpressRoute` | |
| Application Gateway | `Application Gateway` | WAF is a tier here, not a product |
| Load Balancer | `Load Balancer` | |
| Azure Front Door | `Azure Front Door` | also offers WAF |
| CDN | `Content Delivery Network` | |
| Azure Firewall | `Azure Firewall` | see also `Azure Firewall Manager` |
| Traffic Manager | `Traffic Manager` | |
| Azure Bastion | `Azure Bastion` | |
| DNS / Private DNS | `Azure DNS` | |
| Public IP Addresses | `IP Addresses` | no "Public" |
| Bandwidth / egress | `Bandwidth` | **easy to forget, often material** |
| NAT Gateway | `Azure NAT Gateway` | |
| Private Link | `Azure Private Link` | |
| Virtual WAN | `Virtual WAN` | |

## Security

| Asked for | Calculator name | Note |
|---|---|---|
| Microsoft Sentinel | `Microsoft Sentinel` | |
| Key Vault | `Key Vault` | |
| Azure DDoS Protection | `Azure DDoS Protection` | |
| Microsoft Defender for Cloud | `Microsoft Defender for Cloud` | |
| Dedicated HSM | `Azure Dedicated HSM` | |
| Web Application Firewall | — | a tier of Application Gateway / Front Door |
| Azure Information Protection | — | **not on the calculator** (M365 licensing) |

## Storage

| Asked for | Calculator name | Note |
|---|---|---|
| Blob Storage | `Storage Accounts` | `type` = block blob |
| Archive Storage | `Storage Accounts` | `accessTier` = `archive` |
| Queue / Table Storage | `Storage Accounts` | set `type` |
| Data Lake Storage Gen2 | `Storage Accounts` | `fileStructure` = hierarchical |
| Managed Disks | `Managed Disks` | **search-only**; usually configured *inside* a VM row instead |
| Azure Files | `Azure Files` | |
| Azure NetApp Files | `Azure NetApp Files` | |
| Azure Elastic SAN | `Azure Elastic SAN` | **search-only** |
| Azure Managed Lustre | `Azure Managed Lustre` | |

## Web / mobile / integration

| Asked for | Calculator name |
|---|---|
| API Management | `API Management` |
| Service Bus | `Service Bus` |
| Event Grid | `Event Grid` |
| Event Hubs | `Event Hubs` |
| Logic Apps | `Logic Apps` |
| Notification Hubs | `Notification Hubs` |
| SignalR Service | `Azure SignalR Service` |
| App Configuration | `App Configuration` |
| Azure Communication Services | `Azure Communication Services` |

## Identity

| Asked for | Calculator name |
|---|---|
| Microsoft Entra ID | `Microsoft Entra ID (formerly Azure AD)` |
| Azure AD B2C | `Azure Active Directory B2C` |
| Entra External ID | `Microsoft Entra External ID` |

---

## Not priceable on the calculator

Say so explicitly in the BoQ rather than omitting them silently — they still
cost the customer money, just not through this tool:

- **Azure Sphere** · **Azure Stack Hub** · **Azure Blueprints**
- **Azure Information Protection** — licensed through Microsoft 365
- **Web Application Firewall** — a tier of Application Gateway / Front Door
- Support plans — set on the estimate, not added as a product

## Re-verifying

This catalogue reflects the calculator at the time of writing. Microsoft renames
products (the Foundry rebrand is recent), so if `__addProduct` fails, re-derive
the name rather than assuming the product was removed:

```js
const s = document.querySelector('input.product-search');
__setNative(s, 'search');  await __sleep(900);
[...document.querySelectorAll('div.service-info-picker-cta.pickerItem')]
  .filter(e => e.offsetParent !== null)
  .map(el => el.querySelector('svg[data-slug-id]')?.querySelector('title')?.textContent.trim());
```

The `data-slug-id` on each card's SVG is a stable machine-readable identifier and
changes less often than the display name.
