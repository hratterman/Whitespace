# Category Whitespace Tool

Analyzes a brand's accessory/add-on catalog against competitors and produces
a category-strategist-grade whitespace and merchandising analysis: where the
brand is leaving money on the table, why, and what specifically to do about
it. The output is a strategic deliverable — a diagnosed, argued, committable
recommendation — not a dashboard of statistics.

## How it's shaped

The work is split along the judgment line:

- **Deterministic code** (`whitespace/`, no model calls): input validation,
  the category-to-bucket mapping, composition shares, comparable-price
  candidates, channel math. Emits `analysis.json` — every share labeled with
  its figure type so mix % and penetration % can never blend.
- **The frontier model** (via the Pro subscription, never a wired API key):
  ambiguous mapping calls, the demand-vs-merchandising diagnosis, benchmark
  selection, opportunity classification, pack generation, and the report
  itself. The method it follows is `method/REASONING.md`; the deliverable
  contract is `method/OUTPUT_SPEC.md`.

Two ways to run the judgment layer:

1. **Agent orchestration (recommended):** open this repo in Claude Code and
   invoke the skill — `/whitespace <data-dir>`. The agent runs the compute
   step, resolves unmapped SKUs, applies the method, and writes
   `<data-dir>/out/report.md`.
2. **Paste seam:** `python3 -m whitespace prompt <data-dir>` writes
   `out/prompt.md` (method + output spec + analysis object in one prompt).
   Paste it into claude.ai and save the response as `report.md`.

## Two modes, graceful degradation

- **Public-data mode** (default): runs on the brand catalog and competitor
  storefront audit alone — composition, assortment audit, pricing on
  comparable items, merchandising assessment, pack generation. Genuinely
  useful on its own.
- **Full-diagnostic mode**: activates automatically when `buyer_behavior.yaml`
  is present — adds attach/spend/mix/channel diagnosis, leakage and recapture,
  and affinity-grounded lifestyle calls. Removing the file cleanly disables
  only this layer.

## Data contract

One directory per analysis:

| File | Required | Contents |
|---|---|---|
| `brand_catalog.csv` | yes | `sku_id,name,raw_category,price,applicability` |
| `competitor_catalog.csv` | yes | `competitor,sku_id,name,raw_category,price` |
| `merchandising.yaml` | yes | brand + per-competitor merchandising attributes (bundles, named packs, curation, bespoke) with a `source` per entry |
| `buyer_behavior.yaml` | optional | attach rate, median spend, channel capture, purchase mix, affinity indices — unlocks full-diagnostic mode |
| `taxonomy.yaml` | optional | overrides the repo-root taxonomy for non-automotive domains |

Data is *supplied*, not scraped: competitor assortment comes from the user or
from a separate model-assisted storefront audit that hands structured data to
the tool. See `examples/meridian/` for a complete (synthetic) fixture and
`examples/meridian/sample-report.md` for what the finished deliverable looks
like.

## The mapping is never a black box

`taxonomy.yaml` holds the explicit category-to-bucket rules. Deterministic
matching runs exact-category → category-keyword → name-keyword; anything
unmatched is surfaced as *unmapped* for the model to resolve with a recorded
reason (appendix of every report). Rules never assign the `other` bucket —
only a deliberate model decision can.

## Quickstart

```bash
pip install -r requirements.txt   # pyyaml only
python3 -m whitespace analyze examples/meridian          # compute layer
python3 -m whitespace prompt examples/meridian           # + paste-seam prompt
python3 -m unittest discover -s tests                    # test suite
```

## Validating on a new brand (the second-brand test)

The tool is real only if it works on a brand it has never seen. To run one:
build the three input files for a brand with no prior hand-analysis (a
storefront audit session with Claude producing the CSVs is the intended
pre-step), run the workflow, and check the output holds up as a genuine,
non-generic strategic read — diagnosis stated, composition gap led,
recommendations committable.

## Confidentiality

When output is shown externally, keep proprietary or licensed inputs out of
it: method and conclusions directionally, no internal or licensed figures.
The `source` fields exist so the report can carry provenance — and so
unverified figures get flagged instead of laundered into fact.
