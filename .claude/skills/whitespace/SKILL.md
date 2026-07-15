---
name: whitespace
description: Guided competitive whitespace analysis for any portfolio-vs-competitors problem - product add-ons, consumables, services & coverage, class schedules, content libraries. Use when the user wants to find where they're leaving value on the table versus competitors, mentions whitespace, assortment, attach, or merchandising gaps, or shows up with catalog/portfolio data - even messy data. Delivers a slide deck, strategist memo, and executive one-pager; no setup knowledge required.
---

<!-- Repo-local variant. Keep the flow in sync with skills/analyze/SKILL.md (plugin variant); only the path/tool references differ. -->

# Whitespace analysis - guided flow

You run the whole tool. The deterministic layer is the `whitespace/` package
in this repo; you are the judgment layer. The user should never need to read
documentation - carry them through every step and never make them format
data themselves.

## How to run the tool

From the repo root:

- Compute CLI: `python3 -m whitespace <cmd>`
- Method (binding): `method/REASONING.md` and `method/OUTPUT_SPEC.md`
- Demo fixture: `examples/meridian` (synthetic; reference deliverable
  `sample-report.md` alongside it)

Requires `pyyaml` - check once with `python3 -c "import yaml"` and
`pip install pyyaml` if missing.

## Fit - the premise system

The method runs wherever there is **a portfolio of offerings, competitors
with portfolios of their own, and (optionally) data on what customers
actually choose**. The frame for a given world is a *premise*
(`premise.yaml` in the data dir). Resolve it early:

1. **Preset match.** `the repo's `premises/` dir which` ships four:
   `attach` (default - core product + add-ons), `replenishment` (consumables
   & install base), `service` (warranties/coverage/care), `portfolio`
   (generic). Copy one in via `init --premise <key>` when it fits.
2. **Derive a custom premise** when the user's world has its own vocabulary
   (class schedules, content libraries, practice areas…). Write
   `premise.yaml` yourself - name the four questions (participation / depth /
   mix / capture) in their world's words, the entity/pack nouns, the channel
   labels, and a `guidance` note - using a preset as the structural template.
   Show the user the frame in two or three sentences and confirm before
   proceeding. Pair it with a domain `taxonomy.yaml` (keep the bucket keys;
   re-label and re-keyword).
3. **Wrong tool.** No competitors to benchmark, no mix dimension, or a
   single-metric-over-time problem: say so honestly and name what analysis
   would fit instead. Never force the frame.

Buyer-behavior data always uses the canonical field names (`attach_rate`,
`median_spend`, `channel_capture` with an `own_channel` key, `purchase_mix`)
- the premise relabels them everywhere the user sees them.

## Step 1 - meet the user where they are

- Argument is a directory containing `brand_catalog.csv` → go to **Analyze**.
- Argument is `demo`, or the user just wants to see what the tool does → **Demo**.
- No argument: search the project for `brand_catalog.csv` (ignore
  `examples/`). Exactly one match → confirm and use it. Several → ask which.
  None → **Onboard**.

## Demo

```
python3 -m whitespace analyze examples/meridian
```

Then run **Reason & write** with output to `examples/meridian/out/report.md`.
Tell the user the fixture is synthetic and that the same flow runs on their
own brand whenever they're ready.

## Onboard - build the data directory conversationally

1. One AskUserQuestion round: the brand/organization name; what world this
   is (to pick or derive the premise); what they have for the portfolio data
   (an export / something they can paste / nothing yet); which 2-3
   competitors matter.
2. Scaffold: `python3 -m whitespace init data/<brand-slug> --brand "<Brand Name>" --premise <key>`
   (omit `--premise` for attach; for a derived premise, write `premise.yaml` into the scaffolded dir yourself)
   ``
3. **Brand catalog** - convert whatever they give you (CSV/XLSX export,
   pasted product list, a document) into `brand_catalog.csv`. Rules: keep the
   storefront's own category names as `raw_category` (the tool's taxonomy
   layer translates them transparently); **never invent prices** - leave
   unknown prices blank and the tool will flag them. Show a preview (first
   rows + SKU count) and get a nod before moving on.
4. **Competitor catalogs** - same conversion per competitor into
   `competitor_catalog.csv`. If they have nothing, offer the model-assisted
   pre-step: with their OK, audit the competitors' public storefront pages
   yourself (fetch/read, structure into rows). The tool itself never scrapes.
5. **Merchandising audit** - fill `merchandising.yaml` from what the
   storefronts show plus a short interview: does each player bundle? named
   packs (get the names)? does the store guide the buyer or just list parts?
   bespoke/made-to-order? Record a `source` (what was audited, when) on every
   entry.
6. **Buyer data** - ask once whether they have buyer-behavior data (attach
   rate, spend per buyer, channel split, purchase mix - e.g. a syndicated
   survey). If yes, convert it into `buyer_behavior.yaml` (rename from the
   scaffolded template; `purchase_mix` is share of *purchases*, sums to 1 -
   not share of buyers). If no, proceed in public-data mode and say in one
   sentence what that file would unlock. Don't push.

## Analyze

```
python3 -m whitespace analyze <data-dir>
```

- Contract errors: explain what's malformed and fix it *with* the user's
  data - never silently repair or fabricate.
- Unmapped SKUs: if more than ~10% of a catalog, copy the root
  `taxonomy.yaml` into the data dir and add exact mappings for that
  storefront's category names; otherwise resolve them individually during
  reasoning.
- Note every data flag; they travel to the report appendix.

## Reason & write (binding)

Read `method/REASONING.md`, `method/OUTPUT_SPEC.md`, and
`method/REPORT_SPEC.md` **in full**, plus the generated `out/analysis.json`.
Resolve every unmapped SKU (bucket + one-line reason → appendix). Apply the
method exactly: diagnose problem *type* before size; lead with composition,
not concentration; benchmark behavior, not presence; merchandise-first
sequencing. Then write BOTH judgment artifacts to `<data-dir>/out/`:

1. `report.md` - the narrative deliverable per OUTPUT_SPEC.md.
2. `report.json` - the same judgments in structured form per REPORT_SPEC.md.

## Render the presentation formats

```
python3 -m whitespace render <data-dir>
```

This produces `deck.html` (a self-contained slide deck: keyboard navigation,
charts, print-to-PDF) and `onepager.html` (executive one-pager) from your
report.json - deterministically, so never hand-write deck HTML. If render
rejects the report, fix the listed fields and re-run.

## Deliver

Send the user all three formats - `deck.html` (render it inline so they see
it immediately), `report.md`, and `onepager.html` - and summarize in 2-3
sentences: the diagnosis, the top recommendation, and the proposed next
step. Offer follow-ups: rerun in full-diagnostic mode when buyer data
arrives, or validate on a second brand.

## Guardrails

- Public-data mode: never fabricate attach, spend, purchase-mix, or channel
  figures. Say which sections are proxy-based.
- Never blend mix % (share of purchases) with penetration % (share of
  buyers); label every figure.
- Keep proprietary or licensed inputs out of any externally-shareable
  version - directional statements only.
- House style: never use em dashes or en dashes in anything you write or
  generate, ever. Use commas, colons, parentheses, or plain hyphens.
