# Quickstart & Walkthrough

From zero to a finished whitespace report - first on the bundled example
(~5 minutes), then on your own brand.

## Part 0 - The no-effort path (Claude Code plugin)

If you use Claude Code, you can skip everything below. Install the plugin:

```
/plugin marketplace add hratterman/Whitespace
/plugin install whitespace@whitespace
```

Then in any project type `/whitespace:analyze` (or just ask for a whitespace
analysis). The skill is fully guided: it offers the demo, scaffolds your data
directory, converts whatever catalog data you have - an export, a pasted
product list, or nothing yet - into the input contract, asks you the few
questions only you can answer (competitors, merchandising observations,
whether you have buyer data), then computes and delivers all three formats -
slide deck, strategist memo, and executive one-pager. The rest
of this guide is for running the pieces yourself.

## Part 0.5 - No Claude Code? The workbench

If you (or whoever you hand this to) only have claude.ai, skip the raw CLI:

```bash
python3 -m whitespace serve data/mybrand
```

opens a local browser workbench: drop files on cards, run the checks, copy
the reasoning prompt with one button, paste it into claude.ai, paste the
reply back, and the deck renders on the page. Everything below still applies
- the workbench is just a friendlier skin over the same steps.

## What you need

- **Python 3.10+** and one dependency: `pip install -r requirements.txt` (PyYAML).
- **A Claude Pro subscription**, reached either through **Claude Code** (the
  recommended path - the whole workflow runs as one command) or **claude.ai**
  (the paste-seam path). No API key is used anywhere; the judgment layer runs
  on your subscription by design.

## Part 1 - Run the bundled example (5 minutes)

The repo ships with a complete synthetic fixture: `examples/meridian/`, a
fictional truck brand with three competitors and buyer-survey data.

### Step 1: Run the deterministic layer

```bash
python3 -m whitespace analyze examples/meridian
```

You'll see a summary like:

```
brand: Meridian Trucks  mode: full-diagnostic
brand SKUs: 33  competitors: Northstar Motors, Copperline Auto, Vantage Trucks

UNMAPPED (3) - the model must resolve these before composition is final:
  [brand] Cabin Air Ionizer  (raw category: Comfort)
  ...
wrote examples/meridian/out/analysis.json
```

This step is pure math - composition shares, price-comparison candidates,
channel gaps - assembled into `out/analysis.json`. Note two things it
surfaces rather than hides: **unmapped SKUs** (categories the rules couldn't
place; the model resolves them later, with reasons recorded) and **data
flags** (anything malformed or unsourced in your inputs).

### Step 2: Run the judgment layer

**Path A - Claude Code (recommended).** Open this repo in Claude Code and type:

```
/whitespace examples/meridian
```

The agent re-runs the compute step, reads the method
(`method/REASONING.md` + `method/OUTPUT_SPEC.md`), resolves the unmapped
SKUs, applies the reasoning, and writes
`examples/meridian/out/report.md`.

**Path B - paste seam (any Claude chat).**

```bash
python3 -m whitespace prompt examples/meridian
```

This writes `examples/meridian/out/prompt.md` - a single self-contained
prompt bundling the method, the output contracts, and the analysis object.
Paste it into claude.ai; the response contains `report.md` followed by a
```json block. Save the block as `out/report.json`, then
`python3 -m whitespace render examples/meridian` produces the deck and
one-pager locally.

### Step 3: Read the result

You get three deliverables in `out/`: `report.md` (the strategist memo),
`deck.html` (a self-contained slide deck - open it, arrow keys to navigate,
⌘P for PDF), and `onepager.html` (executive summary). Compare against the
committed references: `examples/meridian/sample-report.md` and
`sample-deck.html`. A good report leads with the **diagnosis**
(demand problem vs merchandising problem), then the **composition gap**, and
ends with a recommendation split into *committable now from today's catalog*
vs *requires new capability*. If your output reads like a dashboard of
percentages instead of an argument, something went wrong - see
Troubleshooting.

## Part 2 - Run it on your own brand

Scaffold a data directory with commented fill-in templates:

```bash
python3 -m whitespace init data/acme --brand "Acme Bikes" --premise attach
```

`--premise` picks the frame (`attach`, `replenishment`, `service`,
`portfolio`) and copies it in as an editable `premise.yaml`; omit it for
attach economics. For a world none of the presets fit, the Claude Code skill
derives a custom premise for you - see `examples/harborline` for what one
looks like.

That writes header-only CSVs, a commented `merchandising.yaml`, a
`buyer_behavior.template.yaml` (inert until you fill it in and rename it),
and a README recapping what goes where. The Meridian files remain the
worked reference for every format. What goes in each file:

### 1. `brand_catalog.csv` (required)

```csv
sku_id,name,raw_category,price,applicability
AC-101,All-Weather Floor Liners,Floor Liners,129,Model X
```

One row per accessory SKU. `raw_category` is whatever the brand's own
storefront calls it - don't pre-translate it; the taxonomy layer does that
transparently. `applicability` (model/line/segment) can be blank.

### 2. `competitor_catalog.csv` (required)

```csv
competitor,sku_id,name,raw_category,price
Rival Co,RV-01,Premium Floor Liner Set,Floor Liners,149
```

Same idea, with a `competitor` column. Two or three competitors is enough;
include at least one you suspect does merchandising well. Collect this by
auditing public storefronts - by hand, or ask Claude to do a structured
storefront-audit session that outputs this CSV. (Scraping is deliberately
not part of the tool.)

### 3. `merchandising.yaml` (required)

The storefront-behavior audit: for the brand and each competitor, do they
bundle, offer named packs, curate/guide the buyer, offer bespoke? Copy
`examples/meridian/merchandising.yaml` and edit - the fields are
self-explanatory, and each entry takes a `source` (e.g. "storefront audit,
2026-07") so the report can carry provenance.

### 4. `buyer_behavior.yaml` (optional - unlocks full-diagnostic mode)

If you have buyer-survey data (attach rate, median spend, channel split,
purchase mix, affinity indices), fill in the scaffolded
`buyer_behavior.template.yaml` and rename it to `buyer_behavior.yaml` -
the template name is deliberately inert so a half-filled file can't
accidentally activate the diagnostic layer. **Without this file the tool
still runs** - it degrades cleanly to public-data mode (composition,
pricing, merchandising critique, packs) and simply won't claim behavioral
facts it can't see.

Mind the two figure types: `purchase_mix` is share of *purchases* (sums
to 1); `attach_rate` is the only share-of-*buyers* figure. Don't put
penetration numbers in the mix fields - the validator flags sums that
don't reach ~1.0 but won't repair them.

### 5. `taxonomy.yaml` (optional override)

The repo-root taxonomy is tuned for vehicle accessories. For another domain
(appliances, bikes, cameras…), copy it into your data directory and swap the
keyword rules for domain-appropriate ones; the bucket *types* (commodity/
protection, visible personalization, utility, performance, lifestyle) carry
across domains. A local `taxonomy.yaml` overrides the root one automatically.

### 6. Run it

```bash
python3 -m whitespace analyze data/acme     # sanity-check inputs first
```

Fix anything it complains about (missing columns, malformed prices), skim
the unmapped list - if it's long, add exact mappings for your storefront's
category names to the taxonomy - then run `/whitespace data/acme` in Claude
Code, or the `prompt` subcommand + paste as above. The deliverable lands in
`data/acme/out/report.md`.

## Reading the report with the right skepticism

- **Every percentage is labeled** with its figure type (purchase mix /
  catalog share / attach / channel share). Catalog share is what the brand
  *offers*; only purchase mix is what buyers *do*. The report must never
  present one as the other.
- **The appendix is part of the deliverable**: it records every
  category-to-bucket call the model made (with reasons), which
  price-comparison pairs it rejected as not truly comparable, and every data
  flag carried through. If the appendix is missing, the run didn't follow
  the method.
- **Halo opportunities** (pet, fragrance, tech-adjacent) should be labeled
  halo and never sized as volume. A report that sizes a pet-accessory
  opportunity in dollars is over-claiming.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `error: required input missing: …/brand_catalog.csv` | Wrong directory, or file misnamed. All three required files must be in the data dir. |
| `missing columns ['raw_category']` | Header row doesn't match the contract exactly - compare against the example CSVs. |
| Long unmapped list | Your storefront's category names aren't in the taxonomy. Add them under `mapping.exact` in a local `taxonomy.yaml` - or let the model resolve them (fine for a handful, tedious for fifty). |
| `purchase_mix sums to 0.80…` flag | You've probably supplied penetration figures where mix figures belong. Fix the source data; the tool won't rescale. |
| Report reads generic / like a data dump | The model likely didn't get the method. Use the skill or the emitted `prompt.md` verbatim - the method and output contract must travel with the data. |
| No behavioral claims in the report | Correct behavior in public-data mode: without `buyer_behavior.yaml`, attach/spend/mix/channel facts would be fabrication. Supply the file to unlock them. |
