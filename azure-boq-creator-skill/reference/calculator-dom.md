# Azure Pricing Calculator — DOM reference and failure modes

Verified against `https://azure.microsoft.com/en-us/pricing/calculator/` (2026).
The calculator is a React app. Everything below was confirmed by driving a real
95-line-item estimate end to end.

---

## Canvas wiring

```
open_canvas canvasId="browser" instanceId="azure-calc"
            input={"url":"https://azure.microsoft.com/en-us/pricing/calculator/"}
```

`page_id` for `read_page` / `evaluate_javascript` / `screenshot_page` is **the
`instanceId` you chose**. There is no separate `open_browser_page` call.

`read_page` truncates its element list around `e80` and does **not** expose the
`<select>` controls. Use `evaluate_javascript` for anything beyond a first look.

---

## Setting values on a React app

Assigning `el.value` does nothing — React overwrites it. Use the native setter
and dispatch both events:

```js
function setNative(el, val) {
  const proto = el.tagName === 'SELECT'
    ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, val);
  el.dispatchEvent(new Event('input',  { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}
```

Radios and dropdown options are the exception — call `.click()` on those.

Confirm it worked by watching the total change, not by reading `el.value` back.

---

## Row structure

| What | Selector |
|---|---|
| One product row | `.wa-calcService` |
| All rows | `document.querySelectorAll('.wa-calcService')` |
| Row header / collapse toggle | `button.module-name` (`aria-expanded`) |
| Add a VM | first visible `button` whose text is `Add to estimate` |
| Clone / Delete row | `button.calculator-button.clone` / `.delete` |
| Export | `button.export-button` |
| Estimate name | `input[name="estimate-name"]` |

### Controls inside a row

| Field | Selector | Values |
|---|---|---|
| Region | `select[name=region]` | `qatar-central`, `europe-west`, `us-east`, … |
| OS | `select[name=operatingSystem]` | `linux`, `windows` |
| Type | `select[name=type]` | `os-only`, `sql`, `biztalk`, `ubuntu`… (varies by OS) |
| Tier | `select[name=tier]` | `basic`, `standard` |
| Category | `select[name=category]` | `all`, `generalpurpose`, `memoryoptimized`… |
| Instance search | `input.instancesSearchDropdown__input` | type here |
| Instance options | `.instancesSearchDropdown__option` | click one |
| Selected SKU | `input[name=size]` (hidden) | e.g. `d8sv5`, `fx64msv2` |
| VM count | `input[name=count]` | |
| Hours | `input[name=hours]` | disappears when a reservation is selected |
| Row label | `input[name=displayName]` | |
| Compute billing | `input[type=radio][value=…]` | `payg`, `sv-one-year`, `sv-three-year`, `one-year`, `three-year` |
| OS billing | `input[type=radio][value=…]` | `payg`, `ahb` (Azure Hybrid Benefit) |
| Payment | `select[name=computePaymentOption]` | `monthly`, `upfront` |

### Managed disks (collapsed submodule)

Expand first: `button.toggle-submodule-btn` whose text starts `Managed Disks`.

| Field | Selector | Values |
|---|---|---|
| Disk family | `select[name=managedDiskTier]` | `standardhdd`, `standardssd`, `premiumssd`, `premiumssdv2` |
| Disk size | `select[name=managedDiskType]` | prefix follows family: `s4…s80` / `e4…e80` / `p4…p80` |
| Disk count | `input[name=managedDisks]` | defaults to `0` |

Size codes map to GiB: `4`=32, `6`=64, `10`=128, `15`=256, `20`=512, `30`=1024,
`40`=2048, `50`=4096, `60`=8192, `70`=16384, `80`=32767.

Changing the family **replaces the size option list** — always re-set
`managedDiskType` after `managedDiskTier`, and verify the code exists first.

---

## Failure modes

### 1. `evaluate_javascript` times out after ~5s — the page keeps running
The eval wrapper gives up, but your async work still completes. Don't fight it:

```js
window.__stat = { done: 0, total: N, running: true, errors: [] };
(async () => {
  for (let i = 0; i < N; i++) { /* … */ __stat.done = i + 1; }
  __stat.running = false;
})();
return { started: true };          // returns immediately
```

Then poll with a **tiny** call: `return {done:__stat.done, running:__stat.running}`.
Keep poll payloads small — large returns time out on a heavy page.

### 2. Collapsed rows have no controls in the DOM
When a row is collapsed, everything inside is unmounted. `displayName`, `region`,
`size` all read as `undefined` and it looks like your data vanished. It hasn't.

Read the label from `button.module-name` (`"Virtual Machines: <displayName>"`),
expand → edit → collapse. Keeping 95 rows expanded makes every eval time out, so
collapse as you go.

### 3. Changing region silently resets the reservation to `payg`
Always set region **before** billing, and re-audit billing afterwards.

### 4. Not every SKU offers a Reserved Instance
Fsv2 (`F4s v2`, `F8s v2`) has no 1-yr or 3-yr RI — the radios are `disabled` and
the row shows *"3 year reserved option is not available for your instance
selection."* Fall back to `sv-three-year` (3-yr Savings Plan, ~53%) and tell the
user which rows and why.

### 5. The instance search has a matching quirk
Searching the full name sometimes returns **nothing** (`"F8s v2"` → 0 options)
while a substring works (`"8s v2"` → includes `F8s v2`). Always implement a
fallback: try the full SKU, and if there are no options, retry with the SKU minus
its leading letters, then match the option whose text starts `"<SKU>:"`.

Clear the input (`setNative(inp,'')`) before retyping, or stale filtering sticks.

### 6. A heavily-reconfigured row can wedge permanently
A row reused many times can stop returning search results while an identical
fresh row works fine. Don't keep retrying — **clone a healthy row**
(`button.calculator-button.clone`), configure the clone, then delete the wedged
row. Note that Clone appends to the **end** of the list, not next to its source.

### 7. There is no "Delete all"
Only per-row `Delete` buttons. To rebuild, either reuse existing rows in place
(faster) or delete them one at a time.

### 8. Rebuilds are slow and get slower
~4s per row early on, ~12s once the page holds 90+ rows. Budget ~15 min for 95
rows. Poll every 2–5 minutes rather than continuously.

### 9. A fresh page has a phantom empty `.wa-calcService`
Before any VM is added, one `.wa-calcService` div exists with no controls and no
`button.module-name`. A naive `querySelectorAll('.wa-calcService')` reports
`rows: 1` on an empty estimate, and a build loop then tries to configure it and
fails with "expand failed". Always filter:

```js
[...document.querySelectorAll('.wa-calcService')]
  .filter(r => r.querySelector('button.module-name') || r.querySelector('select[name=region]'))
```

### 10. Fields silently VANISH on an unsupported region/option combination
The biggest trap for non-VM products. Dropdowns list options the selected
region does not actually support, and when you pick one the calculator
**removes the pricing controls from the DOM instead of showing an error**.

Verified example — Storage Accounts:

| Region | Redundancy | Result |
|---|---|---|
| Qatar Central | `lrs` | 8 selects, 5 number inputs — fine |
| Qatar Central | `grs` | 7 selects, **0 number inputs** — capacity/transaction fields gone |
| East US | `grs` | 11 selects, 8 number inputs — fine |

Note Qatar Central still *offers* `grs`, `ra-grs`, `gzrs`, `ra-gzrs` in the
dropdown. The list is not region-filtered.

So: if `__cfgGeneric` reports missed fields and the row summary looks
truncated, **suspect the region/option pair before suspecting your code**.
Re-test the same spec against `us-east`; if the fields reappear there, the
combination is unsupported and you must pick a different option or region.
Always surface this to the user — silently pricing LRS when they asked for GRS
would be a real costing error.

### 11. Non-VM products need one change at a time
Setting several selects in quick succession can wedge a row (its inputs
disappear and do not come back). `__cfgGeneric` therefore applies one field per
step, re-queries the row each time, and retries over several passes. Keep the
settle delay at ~900 ms.

### 12. Quantities are in GB, and defaults are dangerous
Number inputs take **GB**, so 5 TB is `5120`. There is no unit selector on most
products (Storage Accounts is the exception, via `storageUnits` = `1` or `1024`).

Worse, every non-VM product ships with plausible defaults that quietly survive:
Bandwidth defaults to **5 GB from us-west**, which prices **$0.00** because the
first 100 GB/month of egress is free. A row can therefore look configured, carry
a confident label, and contribute nothing to the total.

Two rules:
- **Row labels are free text.** Nothing validates "5 TB" in a label against the
  configuration. Never treat a label as evidence.
- **Non-VM products have their own region fields.** Bandwidth uses `sourceRegion`,
  not `region`, so setting the estimate's region does not touch it.

Run `__auditCosts(targetRegion)` before quoting any total — it flags
`ZERO_COST`, `LABEL_QTY_NOT_IN_ROW` and `REGION_MISMATCH`.

### 13. `hoursFactor` MULTIPLIES the hours field
Several products pair a quantity with a unit multiplier — `computeHoursFactor`
on Fabric, `hoursFactor` on Virtual Machines and App Service, and the various
`*Factor` selects on Azure Files and SQL Database. The total is
**quantity × factor**, not quantity expressed in that unit.

Setting factor = `730` (Month) **and** hours = `730` means 730 months. Verified
on a Fabric F256 row:

| computeHoursFactor | computeHours | Monthly |
|---|---|---|
| `730` (Month) | `730` | **$30,013,020** ← 730x too high |
| `1` (Hours) | `730` | **$41,308** ← correct |

For one month of continuous use, set factor `1` with quantity `730`, or factor
`730` with quantity `1`.

`__auditCosts` will **not** catch this — the row is neither zero-cost nor
region-mismatched, it is simply multiplied wrong. A 730x error is obvious, but
the same mistake with factor = `24` (Days) gives a 24x error that can look
plausible. Sanity-check any row carrying a `*Factor` select against a rough
expected unit price before quoting.

---

## Verification

`get_range` on an Excel canvas shows `#ERROR!` for cross-sheet `SUMIF`/`COUNTIF`
— the preview engine doesn't resolve them. Same-sheet formulas evaluate fine.
Write static values for anything the user needs to read.

Cheapest independent check of a built estimate is the collapsed row summary text:

```
1 D8s v5 (8 vCPUs, 32 GB RAM) (3 year reserved), Windows (License included),
OS Only; 1 managed disk – P30; …
```

Regex that for commitment and disk to confirm every row, without expanding any.

Note the exported workbook total can sit slightly **below** the on-page total —
the export omits the small default inter-region bandwidth allowance the page
includes. Reconcile rather than assuming an error.
