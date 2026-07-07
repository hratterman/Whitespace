# report.json — the structured judgment artifact

Alongside the narrative `report.md`, the reasoning layer writes `report.json`
to the same `out/` directory. It carries the *judgment* content of the
analysis in structured form; `python3 -m whitespace render <data-dir>` then
combines it with `analysis.json` (which supplies all chart data) to produce
the presentation deliverables — `deck.html` (slide deck) and `onepager.html`
(executive one-pager) — deterministically, so every deck is polished and
chart-accurate without the model hand-writing HTML.

Rules of the file:

- Prose fields hold finished, presentation-ready sentences — the same
  editorial standard as `report.md`, not notes.
- Numbers quoted in prose must come from `analysis.json` or be clearly
  derived arithmetic; the renderer never checks your math, the method does.
- Omit a section (or set it `null`) when the mode doesn't support it — e.g.
  `channel` in public-data mode. The renderer skips missing slides.
- `display` strings in the diagnosis pattern are human-formatted ("64%",
  "$310") because the renderer does no number formatting.

## Schema (all fields strings unless noted)

```jsonc
{
  "title": "deck title — the thesis, not the topic",
  "subtitle": "one line: scope, mode, date",
  "badge": "optional chip shown on every slide, e.g. 'Synthetic demonstration data'",
  "why_it_matters": "the money-at-stake framing, 1-2 sentences",

  "diagnosis": {
    "verdict": "short verdict line, e.g. 'A merchandising problem — not a demand problem'",
    "narrative": "the argument, 2-4 sentences",
    "pattern": [                      // full-diagnostic mode: exactly the 4 questions; public mode: []
      { "question": "Attach", "sub": "do buyers buy anything?",
        "brand_display": "64%", "benchmark_display": "66% (Northstar)",
        "read": "Normal — demand exists", "tone": "good|warn|bad" }
    ]
  },

  "composition": {
    "headline": "takeaway headline for the composition slide",
    "narrative": "2-3 sentences",
    "source": "purchase_mix | catalog_share",   // which analysis dataset to chart
    "entities": ["Meridian Trucks", "Northstar Motors", "Copperline Auto"],  // chart series, brand first (≤4)
    "callout_bucket": "exterior_personalization" // optional: bucket to highlight
  },

  "benchmark_note": { "headline": "...", "narrative": "the behavior-vs-presence argument" },

  "channel": null | {                  // full-diagnostic mode only
    "headline": "...", "narrative": "...",
    "entities": ["Meridian Trucks", "Northstar Motors"]   // brand first
  },

  "storefront_critique": { "headline": "...", "bullets": ["...", "..."] },

  "merchandising_benchmark": { "headline": "...", "narrative": "..." },  // table auto-built from analysis

  "packs": {
    "headline": "...", "narrative": "affinity grounding / hypothesis framing",
    "items": [ {
      "name": "Basecamp Pack", "target": "Talon · the camping weekender",
      "grounding": "affinity 124", 
      "skus": [ { "name": "Basecamp Bed Tent", "price": "$329", "exists": true } ],  // exists:false flags a new-product item
      "component_sum": "$765", "bundle_price": "$699"
    } ]
  },

  "pricing_note": { "headline": "...", "narrative": "..." },

  "recommendation": {
    "now":  [ { "action": "short imperative", "detail": "one sentence" } ],   // required, ≥1
    "next": [ { "action": "...", "detail": "..." } ]
  },

  "next_step": { "headline": "...", "narrative": "the one concrete, low-cost close" },

  "appendix": {
    "mapping_resolutions": [ { "sku": "MR-6001 Cabin Air Ionizer", "bucket": "lifestyle_whitespace", "reason": "..." } ],
    "comparability_calls": [ "Bed Cargo Divider vs Bed Cargo Net — rejected: different products" ],
    "data_flags": [ "..." ],          // carry through every analysis.json flag
    "figure_types_note": "one paragraph defining the figure types used"
  }
}
```

Required: `title`, `why_it_matters`, `diagnosis.verdict`,
`diagnosis.narrative`, `composition` (with valid `source`),
`recommendation.now` non-empty, `next_step`, `appendix.data_flags` (may be
empty only when analysis.json's are). The renderer validates and refuses
with a field list rather than emitting a broken deck.
