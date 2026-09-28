# Impact model

How much time this actually returns, what the numbers assume, and how to re-run
the model with your own figures.

Everything here is either **measured** in a real run or a **stated assumption**.
Nothing is asserted without its basis.

```bash
python tools/impact_model.py                      # defaults
python tools/impact_model.py --vms 200 --scenarios 4 --boqs-per-year 15
```

---

## The inputs

| Input | Value | Where it comes from |
|---|---|---|
| Interactions per VM | **20** | **Measured** — counted from the fields the harness sets in `__cfgRow`: add row, region, OS, instance search (3), count, billing radio, expand disks, disk family, disk size, disk count, row name |
| Seconds per interaction | **4** | **Assumption.** Includes reading, scrolling, waiting for the page to settle. Deliberately conservative — a fast operator on a quiet page beats this; anyone cross-referencing a spreadsheet does not |
| Driver seconds per row | **7** | **Measured** — 95-row conversion run, timed across the full pass |
| Setup + review per scenario | **5 min** | **Assumption.** Attaching the file, answering the scoping questions, reviewing the audit output |

The two assumptions are the only soft numbers. Both are stated so you can
substitute your own.

---

## What the model does *not* count

Deliberately excluded, because they would inflate the result:

- **Error correction.** Finding and fixing a mis-priced line by hand is not in the
  manual figure, even though it is real.
- **Context switching.** Two hours of clicking is rarely two uninterrupted hours.
- **Rework from stale exports.** Failure mode 14 alone cost a full rebuild before
  it was understood.
- **The value of catching an error.** A $602/month line priced at $0.00 is 24% of
  an estimate. There is no honest hourly rate for that.

The model is therefore a **floor**, not a ceiling.

---

## Per-BoQ

| Estate | Scenarios | Manual | With skill | Saved | Ratio |
|---|---:|---:|---:|---:|---:|
| 25 VMs | 1 | 33 min | 8 min | 25 min | 4.2x |
| 25 VMs | 3 | 100 min | 24 min | 76 min | 4.2x |
| 50 VMs | 1 | 67 min | 11 min | 56 min | 6.2x |
| 50 VMs | 3 | 200 min | 32 min | 168 min | 6.2x |
| **95 VMs** | **1** | **127 min** | **16 min** | **111 min** | **7.9x** |
| **95 VMs** | **3** | **380 min** | **48 min** | **5.5 hrs** | **7.9x** |
| 200 VMs | 1 | 267 min | 28 min | 238 min | 9.4x |
| 200 VMs | 3 | 800 min | 85 min | 11.9 hrs | 9.4x |

**The ratio improves with estate size**, because the skill's fixed overhead
(setup, review) is amortised while manual effort scales linearly.

**Attended vs unattended matters more than the ratio.** The manual column is all
keyboard time. Most of the skill's column is a driver running while you do
something else.

---

## Why scenarios multiply

A BoQ is rarely priced once. The commercial shape moves:

> "What does this look like pay-as-you-go?"
> "What if we only commit on production?"
> "Can we see it with Hybrid Benefit applied?"
> "The customer wants it in West Europe instead."

Each of those is **every row again** by hand. With the skill it is one instruction.

This is measured, not theoretical: a 95-line BoQ in this repo's validation set was
re-priced end to end from 3-year Reserved Instance to pay-as-you-go —
**95 of 95 rows converted, disks intact, zero errors, unattended.** The same
change by hand is another ~1,900 interactions.

Two to four scenarios per deal is normal. The model defaults to three.

---

## Annualised

Time returned per person, at a 95-VM estate with 3 scenarios:

| BoQs / year | Hours returned |
|---:|---:|
| 5 | ~28 h |
| 10 | ~55 h |
| 20 | ~111 h |
| 40 | ~221 h |

Substitute your own volume — `--boqs-per-year` on the script.

---

## Frequency: how often does this occur?

Every one of these needs a BoQ:

- A migration assessment
- A landing-zone proposal
- A modernisation business case
- A datacentre-exit costing
- A renewal where the customer wants to re-shape commitment
- Any competitive bid with a cost component

It is not an edge case or a once-a-quarter task. For an SE or CSA working
migration deals, it is **recurring work that arrives with every opportunity** —
and it arrives at the least convenient moment, because the BoQ is usually needed
before the deal is qualified enough to justify a day on it.

That timing is part of the pain. A two-hour task that must be done *now*, on an
estate that might not close, is exactly the work worth automating.

---

## The half that isn't time

The model above prices effort. It does not price **being wrong**.

The calculator has 14 documented failure modes that produce a wrong number rather
than an error — silent reservation resets, vanishing pricing fields, a
multiplying hours factor, defaults that price at zero.

One real example from building this: a bandwidth line labelled "5 TB" sitting at
the default 5 GB in the wrong region, pricing at **$0.00**. That was
**$602/month — 24% of the estimate.** The total looked entirely reasonable. No
review that checks totals would have caught it.

The skill now audits every line for exactly that class of error before it quotes
anything. The value of that is not hours saved — it is a number you can defend in
front of a customer.

---

## Re-running it

`tools/impact_model.py` takes every assumption as a flag, so you can argue with it:

```bash
# more pessimistic about the skill, more generous about manual speed
python tools/impact_model.py --sec-per-click 3 --setup-min 10

# your actual portfolio
python tools/impact_model.py --vms 140 --scenarios 2 --boqs-per-year 18
```

If your numbers differ, use yours. The point of publishing the model rather than
a headline figure is that the assumptions are visible and contestable.
