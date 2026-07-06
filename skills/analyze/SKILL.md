---
name: analyze
description: Guided category whitespace & merchandising analysis. Use when the user wants to analyze a brand's accessory/add-on assortment vs competitors, mentions whitespace, attach rate, assortment gaps, or merchandising strategy, or shows up with product catalog data — even messy data. Walks from zero to a strategist-grade report; no setup knowledge required.
---

<!-- Plugin variant. Keep the flow in sync with .claude/skills/whitespace/SKILL.md (repo-local variant); only the path/tool references differ. -->

# Whitespace analysis — guided flow

You run the whole tool. The deterministic layer ships inside this plugin;
you are the judgment layer. The user should never need to read documentation
— carry them through every step and never make them format data themselves.

## How to run the tool

Everything ships at `${CLAUDE_PLUGIN_ROOT}`:

- Compute CLI: `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m whitespace <cmd>`
- Method (binding): `${CLAUDE_PLUGIN_ROOT}/method/REASONING.md` and `OUTPUT_SPEC.md`
- Demo fixture: `${CLAUDE_PLUGIN_ROOT}/examples/meridian` (synthetic; reference
  deliverable `sample-report.md` alongside it)

Requires `python3` with `pyyaml` — check once with `python3 -c "import yaml"`
and `pip install pyyaml` if missing. Write all data and outputs under the
user's project (e.g. `whitespace/<brand>/`), never into the plugin directory.

## Step 1 — meet the user where they are

- Argument is a directory containing `brand_catalog.csv` → go to **Analyze**.
- Argument is `demo`, or the user just wants to see what the tool does → **Demo**.
- No argument: search the project for `brand_catalog.csv`. Exactly one match →
  confirm and use it. Several → ask which. None → **Onboard**.

## Demo

```
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m whitespace analyze "${CLAUDE_PLUGIN_ROOT}/examples/meridian" --out ./whitespace-demo
```

Then run **Reason & write** with output to `./whitespace-demo/report.md`.
Tell the user the fixture is synthetic and that the same flow runs on their
own brand whenever they're ready.

## Onboard — build the data directory conversationally

1. One AskUserQuestion round: the brand name; what they have for its catalog
   (a storefront export / something they can paste / nothing yet); which 2–3
   competitors matter.
2. Scaffold: `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m whitespace init whitespace/<brand-slug> --brand "<Brand Name>"`
3. **Brand catalog** — convert whatever they give you (CSV/XLSX export,
   pasted product list, a document) into `brand_catalog.csv`. Rules: keep the
   storefront's own category names as `raw_category` (the tool's taxonomy
   layer translates them transparently); **never invent prices** — leave
   unknown prices blank and the tool will flag them. Show a preview (first
   rows + SKU count) and get a nod before moving on.
4. **Competitor catalogs** — same conversion per competitor into
   `competitor_catalog.csv`. If they have nothing, offer the model-assisted
   pre-step: with their OK, audit the competitors' public storefront pages
   yourself (fetch/read, structure into rows). The tool itself never scrapes.
5. **Merchandising audit** — fill `merchandising.yaml` from what the
   storefronts show plus a short interview: does each player bundle? named
   packs (get the names)? does the store guide the buyer or just list parts?
   bespoke/made-to-order? Record a `source` (what was audited, when) on every
   entry.
6. **Buyer data** — ask once whether they have buyer-behavior data (attach
   rate, spend per buyer, channel split, purchase mix — e.g. a syndicated
   survey). If yes, convert it into `buyer_behavior.yaml` (rename from the
   scaffolded template; `purchase_mix` is share of *purchases*, sums to 1 —
   not share of buyers). If no, proceed in public-data mode and say in one
   sentence what that file would unlock. Don't push.

## Analyze

```
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}" python3 -m whitespace analyze <data-dir>
```

- Contract errors: explain what's malformed and fix it *with* the user's
  data — never silently repair or fabricate.
- Unmapped SKUs: if more than ~10% of a catalog, copy
  `${CLAUDE_PLUGIN_ROOT}/taxonomy.yaml` into the data dir and add exact
  mappings for that storefront's category names; otherwise resolve them
  individually during reasoning.
- Note every data flag; they travel to the report appendix.

## Reason & write (binding)

Read `${CLAUDE_PLUGIN_ROOT}/method/REASONING.md` and
`${CLAUDE_PLUGIN_ROOT}/method/OUTPUT_SPEC.md` **in full**, plus the generated
`out/analysis.json`. Resolve every unmapped SKU (bucket + one-line reason →
appendix). Apply the method exactly: diagnose problem *type* before size;
lead with composition, not concentration; benchmark behavior, not presence;
merchandise-first sequencing. Write the deliverable to `<data-dir>/out/report.md`
following the output spec — headline-led sections, every claim paired with
evidence and an action.

## Deliver

Send the user `report.md` and summarize in 2–3 sentences: the diagnosis, the
top recommendation, and the proposed next step. Offer follow-ups: rerun in
full-diagnostic mode when buyer data arrives, or validate the tool on a
second brand.

## Guardrails

- Public-data mode: never fabricate attach, spend, purchase-mix, or channel
  figures. Say which sections are proxy-based.
- Never blend mix % (share of purchases) with penetration % (share of
  buyers); label every figure.
- Keep proprietary or licensed inputs out of any externally-shareable
  version — directional statements only.
