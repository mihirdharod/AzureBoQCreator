/* ------------------------------------------------------------------------
 * Azure Pricing Calculator harness
 *
 * Paste the whole file through `evaluate_javascript` once to install helpers
 * on `window`, then drive it with short follow-up calls.
 *
 * Because evaluate_javascript times out after ~5s while the page keeps
 * running, long work MUST be launched fire-and-forget and polled via
 * window.__stat. See runPlan() at the bottom.
 *
 * A plan item looks like:
 *   { l:"App | SRV01 | D8s v5 | Premium SSD ~460GB",   // row label
 *     s:"D8s v5",            // SKU as shown in the instance dropdown
 *     o:"windows",           // "windows" | "linux"
 *     r:"qatar-central",     // region value
 *     n:1,                   // VM count
 *     b:"three-year",        // payg | one-year | three-year | sv-one-year | sv-three-year
 *     ahb:false,             // Azure Hybrid Benefit (Windows only)
 *     t:"premiumssd",        // standardhdd | standardssd | premiumssd | premiumssdv2
 *     c:"p20",               // disk size code, prefix must match t
 *     dn:1 }                 // disk count
 * --------------------------------------------------------------------- */

window.__sleep = ms => new Promise(r => setTimeout(r, ms));

window.__setNative = function (el, val) {
  const proto = el.tagName === 'SELECT'
    ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, val);
  el.dispatchEvent(new Event('input',  { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
};

window.__rows = () => [...document.querySelectorAll('.wa-calcService')]
  .filter(r => r.querySelector('button.module-name') || r.querySelector('select[name=region]'));
window.__label = r => {
  const b = r.querySelector('button.module-name');
  return (b ? b.innerText : '').replace(/\s+/g, ' ').replace(/^[^:]*:\s*/, '').trim();
};

/* ---------- expand / collapse -------------------------------------------
 * Collapsed rows unmount their controls entirely. Always expand before
 * reading or writing, and collapse afterwards to keep the page responsive. */
window.__expand = async function (r) {
  const b = r.querySelector('button.module-name');
  if (b && b.getAttribute('aria-expanded') !== 'true') b.click();
  for (let k = 0; k < 30; k++) {
    await __sleep(150);
    if (r.querySelector('select[name=region]')) return true;
  }
  return !!r.querySelector('select[name=region]');
};

window.__collapse = function (r) {
  const b = r.querySelector('button.module-name');
  if (b && b.getAttribute('aria-expanded') === 'true') b.click();
};

/* ---------- add any product by name -------------------------------------
 * The product search chokes on full names with parentheses
 * ("Azure Kubernetes Service (AKS)" returns nothing, "Kubernetes" works),
 * so fall back through progressively shorter queries. */
window.__addProduct = async function (name) {
  const before = __rows().length;
  const s = document.querySelector('input.product-search');
  const base = name.replace(/\s*\([^)]*\)\s*/g, ' ').trim();
  const words = base.split(/\s+/).filter(w => !/^(azure|for|the|and|service|services)$/i.test(w));
  const queries = [name, base, words.slice(-2).join(' '), words[words.length - 1], words[0]];
  const seen = new Set();

  for (const q of queries) {
    if (!q || seen.has(q.toLowerCase())) continue;
    seen.add(q.toLowerCase());
    if (s) { s.focus(); __setNative(s, ''); await __sleep(250); __setNative(s, q); await __sleep(1100); }

    const btns = [...document.querySelectorAll('button')]
      .filter(b => /Add to estimate/i.test(b.innerText || '') && b.offsetParent !== null);
    const title = b => { const c = b.closest('div'); return (c ? c.innerText : '').split('\n')[0].trim(); };
    let t = btns.find(b => title(b).toLowerCase() === name.toLowerCase())
         || btns.find(b => title(b).toLowerCase() === base.toLowerCase())
         || btns.find(b => title(b).toLowerCase().startsWith(base.toLowerCase()));
    if (t) {
      t.click();
      for (let i = 0; i < 40; i++) {
        await __sleep(250);
        if (__rows().length > before) return { ok: true, via: q, title: title(t) };
      }
    }
  }
  return { ok: false, err: 'product not found: ' + name };
};

/* Virtual Machines is the first card, so this stays valid. */
window.__addVM = async function () {
  const before = __rows().length;
  const btn = [...document.querySelectorAll('button')]
    .filter(b => /Add to estimate/i.test(b.textContent || '') && b.offsetParent !== null)[0];
  if (!btn) return false;
  btn.click();
  for (let i = 0; i < 40; i++) {
    await __sleep(250);
    if (__rows().length > before) return true;
  }
  return false;
};

/* ---------- discover any product's schema -------------------------------
 * Every product uses the same DOM shape - only field names differ - so
 * rather than hardcoding 222 products, read the schema at runtime. */
window.__describeRow = function (row) {
  const q = s => [...row.querySelectorAll(s)];
  const selects = {};
  q('select').forEach(s => { selects[s.name || '?'] = { value: s.value, options: [...s.options].map(o => o.value) }; });
  const numbers = {};
  q('input[type=number]').forEach(i => { numbers[i.name || i.getAttribute('aria-label') || '?'] = i.value; });
  return {
    selects, numbers,
    searchDropdowns: q('input[class*=SearchDropdown__input]').map(i => i.className.split(' ')[0]),
    radios: [...new Set(q('input[type=radio]').map(r => r.value))],
    submodules: q('button.toggle-submodule-btn').map(b => b.innerText.split('\n')[0].trim()),
  };
};

/* ---------- configure any product generically ---------------------------
 * Field sets mutate as you configure (and can vanish entirely - see
 * reference/calculator-dom.md failure mode 10), so apply one field at a
 * time, re-querying the row, and retry anything not yet present. */
window.__cfgGeneric = async function (row, spec, opts) {
  opts = opts || {};
  const settle = opts.settle || 900, passes = opts.passes || 3;

  for (const nm of (spec.expandSubmodules || [])) {
    const t = [...row.querySelectorAll('button.toggle-submodule-btn')]
      .find(x => x.innerText.toLowerCase().includes(nm.toLowerCase()));
    if (t && t.getAttribute('aria-expanded') !== 'true') { t.click(); await __sleep(700); }
  }

  let pending = Object.entries(spec.selects || {}).map(([k, v]) => ['select', k, v])
    .concat(Object.entries(spec.numbers || {}).map(([k, v]) => ['number', k, String(v)]));
  const applied = [];

  for (let pass = 0; pass < passes && pending.length; pass++) {
    const next = [];
    for (const [kind, k, v] of pending) {
      const el = kind === 'select'
        ? row.querySelector(`select[name="${k}"]`)
        : row.querySelector(`input[type=number][name="${k}"]`);
      if (!el) { next.push([kind, k, v]); continue; }
      if (kind === 'select' && ![...el.options].some(o => o.value === v)) { next.push([kind, k, v]); continue; }
      if (el.value !== v) { __setNative(el, v); await __sleep(settle); }
      applied.push(k);
    }
    pending = next;
    if (pending.length) await __sleep(settle);
  }

  if (spec.label) {
    const nm = row.querySelector('input[name=displayName]');
    if (nm) { __setNative(nm, spec.label); await __sleep(400); }
  }
  return { ok: pending.length === 0, applied: [...new Set(applied)],
           missed: pending.map(([kind, k, v]) => `${kind}:${k}=${v}`) };
};

/* ---------- instance picker --------------------------------------------
 * Quirk: the full SKU sometimes returns zero options ("F8s v2") while a
 * substring works ("8s v2"). Try the full name, then fall back. */
window.__pickInstance = async function (row, sku) {
  const inp = row.querySelector('.instancesSearchDropdown__input');
  if (!inp) return { ok: false, err: 'no search input' };

  const queries = [sku, sku.replace(/^[A-Za-z]+/, ''), sku.split(' ')[0]];
  for (const q of queries) {
    if (!q) continue;
    inp.focus(); inp.click();
    __setNative(inp, '');            // clear or stale filtering sticks
    await __sleep(350);
    __setNative(inp, q);
    await __sleep(1000);

    const opts = [...row.querySelectorAll('.instancesSearchDropdown__option')]
      .filter(e => e.offsetParent !== null);
    const want = opts.find(o =>
      o.innerText.trim().toLowerCase().startsWith(sku.toLowerCase() + ':'));
    if (want) { want.click(); await __sleep(900); return { ok: true, via: q }; }
  }
  return { ok: false, err: 'instance not found: ' + sku };
};

/* ---------- billing -----------------------------------------------------
 * Not every SKU offers an RI (Fsv2 has none). Fall back to the 3-yr
 * savings plan and report which fallback was used. */
window.__setBilling = async function (row, want) {
  let used = want;
  let rad = [...row.querySelectorAll(`input[type=radio][value="${want}"]`)][0];
  if (want !== 'payg' && (!rad || rad.disabled)) {
    used = want.startsWith('sv-') ? want
         : (want === 'three-year' ? 'sv-three-year' : 'sv-one-year');
    rad = [...row.querySelectorAll(`input[type=radio][value="${used}"]`)][0];
  }
  if (!rad || rad.disabled) return { ok: false, err: `billing ${want} unavailable` };
  if (!rad.checked) { rad.click(); await __sleep(750); }
  return { ok: true, used };
};

/* ---------- managed disks ---------------------------------------------- */
window.__setDisk = async function (row, tier, code, count) {
  const tg = [...row.querySelectorAll('button.toggle-submodule-btn')]
    .find(x => /Managed Disks/.test(x.innerText));
  if (tg && tg.getAttribute('aria-expanded') !== 'true') { tg.click(); await __sleep(650); }

  const t = row.querySelector('select[name=managedDiskTier]');
  if (!t) return { ok: false, err: 'no disk tier select' };
  __setNative(t, tier);
  await __sleep(850);                       // size list is rebuilt here

  const ty = row.querySelector('select[name=managedDiskType]');
  if (![...ty.options].some(o => o.value === code))
    return { ok: false, err: `disk code ${code} not offered for ${tier}` };
  __setNative(ty, code);
  await __sleep(550);
  __setNative(row.querySelector('input[name=managedDisks]'), String(count));
  await __sleep(350);
  return { ok: true, tier: t.value, code: ty.value };
};

/* ---------- configure one row ------------------------------------------
 * Order matters: region and OS reset downstream fields, and region resets
 * billing — so billing is set after region, never before. */
window.__cfgRow = async function (row, p) {
  const q = s => row.querySelector(s);
  if (!await __expand(row)) return { ok: false, err: 'expand failed' };

  __setNative(q('select[name=region]'), p.r);            await __sleep(350);
  __setNative(q('select[name=operatingSystem]'), p.o);   await __sleep(600);

  const pick = await __pickInstance(row, p.s);
  if (!pick.ok) return pick;

  __setNative(q('input[name=count]'), String(p.n ?? 1)); await __sleep(350);

  const bill = await __setBilling(row, p.b);
  if (!bill.ok) return bill;

  if (p.o === 'windows' && p.ahb) {
    const a = [...row.querySelectorAll('input[type=radio][value="ahb"]')][0];
    if (a && !a.disabled && !a.checked) { a.click(); await __sleep(600); }
  }

  if (p.t && p.c) {
    const d = await __setDisk(row, p.t, p.c, p.dn ?? 1);
    if (!d.ok) return d;
  }

  const nm = q('input[name=displayName]');
  if (nm && p.l) { __setNative(nm, p.l); await __sleep(300); }

  return { ok: true, size: q('input[name=size]').value, billing: bill.used };
};

/* ---------- build the whole plan (fire-and-forget) ---------------------- */
window.runPlan = function (plan, opts) {
  opts = opts || {};
  window.__plan = plan;
  window.__stat = { done: 0, total: plan.length, running: true, errors: [] };
  window.__log  = [];
  (async () => {
    try {
      for (let i = 0; i < plan.length; i++) {
        let row = __rows()[i];
        if (!row) { if (!await __addVM()) { __stat.errors.push({ i, err: 'add failed' }); continue; }
                    row = __rows()[__rows().length - 1]; }
        let res;
        try { res = await __cfgRow(row, plan[i]); }
        catch (e) { res = { ok: false, err: String(e) }; }
        __log.push({ i, l: plan[i].l, ...res });
        if (!res.ok) __stat.errors.push({ i, l: plan[i].l, err: res.err });
        if (opts.collapse !== false) __collapse(row);
        __stat.done = i + 1;
        await __sleep(200);
      }
    } catch (e) { __stat.fatal = String(e); }
    __stat.running = false;
  })();
  return { started: true, total: plan.length };
};

/* Poll with:  return {done:__stat.done, running:__stat.running, nerr:__stat.errors.length}
   Keep poll payloads tiny — big returns time out on a heavy page. */

/* ---------- build a mixed-service plan ----------------------------------
 * Items are either VM items (see the header) or generic product items:
 *   { product:"Storage Accounts", l:"Shared | Blob | 50 TB LRS Hot",
 *     selects:{region:"qatar-central", redundancy:"lrs"},
 *     numbers:{count:50}, expandSubmodules:[] }
 * Anything without `product` is treated as a Virtual Machines item. */
window.runMixedPlan = function (plan, opts) {
  opts = opts || {};
  window.__plan = plan;
  window.__stat = { done: 0, total: plan.length, running: true, errors: [] };
  window.__log = [];
  (async () => {
    try {
      for (let i = 0; i < plan.length; i++) {
        const p = plan[i];
        let res;
        try {
          if (p.product && p.product !== 'Virtual Machines') {
            const add = await __addProduct(p.product);
            if (!add.ok) { res = add; }
            else {
              const row = __rows()[__rows().length - 1];
              await __expand(row);
              res = await __cfgGeneric(row, p, opts);
              if (opts.collapse !== false) __collapse(row);
            }
          } else {
            let row = __rows()[i];
            if (!row) { if (!await __addVM()) { res = { ok: false, err: 'add failed' }; }
                        else row = __rows()[__rows().length - 1]; }
            if (row) { res = await __cfgRow(row, p); if (opts.collapse !== false) __collapse(row); }
          }
        } catch (e) { res = { ok: false, err: String(e) }; }
        __log.push({ i, l: p.l, product: p.product || 'Virtual Machines', ...res });
        if (!res || !res.ok) __stat.errors.push({ i, l: p.l, err: (res && (res.err || res.missed)) || 'unknown' });
        __stat.done = i + 1;
        await __sleep(250);
      }
    } catch (e) { __stat.fatal = String(e); }
    __stat.running = false;
  })();
  return { started: true, total: plan.length };
};

/* ---------- audit -------------------------------------------------------
 * Independent read-back. Never quote a total without running this. */
window.__auditRows = async function (plan) {
  const norm = s => s.toLowerCase().replace(/[^a-z0-9]/g, '');
  const bad = [];
  for (let i = 0; i < plan.length; i++) {
    const p = plan[i], row = __rows()[i];
    if (!row) { bad.push({ i, l: p.l, e: ['missing row'] }); continue; }
    await __expand(row);
    const q = s => row.querySelector(s), e = [];
    if (q('input[name=size]')?.value !== norm(p.s)) e.push('size=' + q('input[name=size]')?.value);
    if (q('select[name=region]')?.value !== p.r)    e.push('region=' + q('select[name=region]')?.value);
    if (q('input[name=count]')?.value !== String(p.n ?? 1)) e.push('count');
    if (p.t && q('select[name=managedDiskTier]')?.value !== p.t) e.push('diskTier');
    if (p.c && q('select[name=managedDiskType]')?.value !== p.c) e.push('diskCode');
    const b = [...row.querySelectorAll('input[type=radio]')].filter(x => x.checked).map(x => x.value)[0];
    if (p.b !== 'payg' && b === 'payg') e.push('billing reverted to payg');
    if (e.length) bad.push({ i, l: p.l, e });
    __collapse(row);
  }
  return { checked: plan.length, mismatches: bad.length, bad: bad.slice(0, 20) };
};

/* Cheap audit with no expanding — parses the collapsed summary line. */
window.__quickAudit = function () {
  const out = __rows().map(r => {
    const t = r.innerText.replace(/\s+/g, ' ');
    const m = t.match(/\d+ [A-Z][^;]*;\s*\d+ managed disks? [^;]*/);
    return m ? m[0] : null;
  });
  return {
    rows: out.length,
    noDisk:       out.filter(s => !s || /0 managed disks/.test(s)).length,
    noCommitment: out.filter(s => s && !/(year reserved|savings plan)/i.test(s)).length,
  };
};

/* ---------- cost audit — RUN THIS BEFORE QUOTING ANY TOTAL --------------
 * Catches the silent costing errors that are invisible in a total:
 *   ZERO_COST              a line item priced $0.00 (unset quantity, or a
 *                          quantity inside a free tier)
 *   LABEL_QTY_NOT_IN_ROW   the label claims "5 TB" but the row is configured
 *                          for something else. Labels are free text and are
 *                          NEVER validated against the configuration.
 *   REGION_MISMATCH        a region field left at its default. Non-VM products
 *                          have their own region selects (Bandwidth uses
 *                          sourceRegion) that the main region never touches.
 * Quantities are entered in GB: 5 TB must be 5120, not 5. */
window.__TIERGB = { 32:'4', 64:'6', 128:'10', 256:'15', 512:'20', 1024:'30',
                    2048:'40', 4096:'50', 8192:'60', 16384:'70', 32767:'80' };

window.__auditCosts = function (targetRegion) {
  const out = __rows().map((r, i) => {
    const t = r.innerText.replace(/\s+/g, ' ');
    const flat = t.replace(/,/g, '');
    const m = t.match(/Monthly:\s*\$([\d,]+(?:\.\d+)?)/);
    const cost = m ? parseFloat(m[1].replace(/,/g, '')) : null;
    const label = (r.querySelector('input[name=displayName]')?.value) || __label(r) || '';
    const flags = [];

    if (cost === 0) flags.push('ZERO_COST');
    if (!label) flags.push('NO_LABEL');

    const lm = label.match(/([\d.,]+)\s*(TB|GB|TiB|GiB)/i);
    if (lm) {
      const n = parseFloat(lm[1].replace(/,/g, ''));
      const gb = Math.round(/^T/i.test(lm[2]) ? n * 1024 : n);
      let seen = new RegExp('\\b' + gb + '\\b').test(flat);
      if (!seen) {                                   // disks show a tier code, not a size
        const code = __TIERGB[gb];
        if (code && new RegExp('\\b[PES]' + code + '\\b', 'i').test(flat)) seen = true;
      }
      if (!seen) {                                   // label size rounded up to a tier
        const cap = Object.keys(__TIERGB).map(Number).sort((a, b) => a - b).find(c => c >= gb);
        if (cap && new RegExp('\\b(?:' + cap + '|[PES]' + __TIERGB[cap] + ')\\b', 'i').test(flat)) seen = true;
      }
      if (!seen) flags.push(`LABEL_QTY_NOT_IN_ROW(${gb}GB)`);
    }

    if (targetRegion) {
      const bad = [...r.querySelectorAll('select')]
        .filter(s => /region/i.test(s.name) && s.value !== targetRegion)
        .map(s => `${s.name}=${s.value}`);
      if (bad.length) flags.push('REGION_MISMATCH:' + bad.join(','));
    }
    return { i, label: label.slice(0, 50), cost, flags };
  });

  return {
    rows: out.length,
    flaggedCount: out.filter(x => x.flags.length).length,
    flagged: out.filter(x => x.flags.length),
    totalMonthly: +out.reduce((a, c) => a + (c.cost || 0), 0).toFixed(2),
  };
};

window.__totals = function () {
  const t = document.body.innerText;
  const g = re => (t.match(re) || [])[0];
  return {
    rows:    __rows().length,
    upfront: g(/Estimated upfront cost\s*\$[\d,.]+/),
    monthly: g(/Estimated monthly cost\s*\$[\d,.]+/),
    annual:  g(/Estimated annual cost\s*\$[\d,.]+/),
  };
};

window.__setEstimateName = function (name) {
  const el = document.querySelector('input[name="estimate-name"]');
  if (el) __setNative(el, name);
  return !!el;
};

window.__export = function () {
  const b = [...document.querySelectorAll('button')]
    .find(x => /^export$/i.test((x.innerText || '').trim()));
  if (!b) return { ok: false, err: 'no export button' };
  b.scrollIntoView({ block: 'center' });
  b.click();
  return { ok: true };
};

return { installed: true, rows: __rows().length };
