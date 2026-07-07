"""`whitespace init`: scaffold a new data directory with fill-in templates.

The buyer-behavior template is written as buyer_behavior.template.yaml on
purpose — the loader only activates full-diagnostic mode on the exact name
buyer_behavior.yaml, so the scaffold runs in public-data mode until the user
deliberately renames the filled-in template.
"""

from __future__ import annotations

from pathlib import Path

from .premise import PRESET_DIR, load_preset

BRAND_CSV = "sku_id,name,raw_category,price,applicability\n"

COMPETITOR_CSV = "competitor,sku_id,name,raw_category,price\n"

MERCHANDISING = """\
# Merchandising attributes from a public storefront audit.
# Fill in the brand and one entry per competitor. Every entry should carry a
# `source` (what was audited, when) — unsourced attributes get flagged.

brand:
  name: YOUR BRAND NAME
  storefront: ""            # e.g. own e-commerce site + dealer counters
  bundles: false            # does the brand sell any bundled offers?
  named_packs: []           # e.g. [Adventure Pack, Work Pack]
  curation_level: none      # none | basic | strong
  curation_notes: ""        # how does the storefront guide (or fail to guide) the buyer?
  bespoke: false            # made-to-order / personalized versions offered?
  notes: ""
  source: ""                # e.g. "storefront audit, 2026-07"

competitors:
  - name: COMPETITOR ONE    # must match the `competitor` column in competitor_catalog.csv
    bundles: false
    named_packs: []
    curation_level: none
    curation_notes: ""
    bespoke: false
    source: ""
"""

BUYER_BEHAVIOR = """\
# OPTIONAL — buyer-behavior data (e.g. a syndicated buyer survey).
# This file is a TEMPLATE and is ignored by the tool. When you have real
# figures, fill it in and rename it to buyer_behavior.yaml to unlock
# full-diagnostic mode. Do not guess values — the tool treats every figure
# here as fact and flags only what it can detect.

source: ""                  # where these figures come from — required for credibility

brand:
  attach_rate: null         # share of buyers purchasing ANY accessory, 0-1
  median_spend: null        # median spend per purchasing buyer
  channel_capture:          # share of accessory purchases by channel, sums to 1
    own_channel: null
    internet: null
    aftermarket_store: null
    other: null
  purchase_mix:             # share of purchases by bucket, sums to 1 (mix %, NOT penetration)
    commodity_protection: null
    exterior_personalization: null
    utility_cargo_towing: null
    performance: null
    lifestyle_whitespace: null
    other: null
  affinity_index: {}        # optional interest indices, 100 = population par
                            # e.g. {camping_outdoors: 124, pets: 97}

benchmarks: []              # same shape per competitor, where you have it:
# - name: COMPETITOR ONE
#   attach_rate: null
#   median_spend: null
#   channel_capture: {own_channel: null, internet: null, aftermarket_store: null, other: null}
#   purchase_mix: {commodity_protection: null, exterior_personalization: null,
#                  utility_cargo_towing: null, performance: null,
#                  lifestyle_whitespace: null, other: null}
"""

DIR_README = """\
# {name}: whitespace-analysis inputs

Fill these in, then run `python3 -m whitespace analyze {dir}`:

1. **brand_catalog.csv** — one row per accessory SKU the brand sells.
   `raw_category` is whatever the brand's storefront calls it (don't
   pre-translate); `price` numeric; `applicability` (model/line) may be blank.
2. **competitor_catalog.csv** — same, with a `competitor` column. Two or three
   competitors is enough; include one you suspect merchandises well.
3. **merchandising.yaml** — the storefront-behavior audit (bundles, named
   packs, curation, bespoke) for the brand and each competitor.
4. **buyer_behavior.template.yaml** — optional. Fill and RENAME to
   `buyer_behavior.yaml` when you have real survey data; it unlocks the
   full attach/spend/mix/channel diagnostic.

Tip: in Claude Code, the guided skill (`/whitespace {dir}` in the tool repo,
`/whitespace:analyze {dir}` with the plugin installed) will carry the whole
flow — including converting a messy product export into brand_catalog.csv.
"""


def init_data_dir(target: str | Path, brand_name: str | None = None,
                  premise: str | None = None) -> list[str]:
    """Create the template files; refuse to overwrite anything. Returns the
    list of files written. `premise` names a preset (attach, replenishment,
    service, portfolio); it is copied in full so the frame stays inspectable
    and editable."""
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    name = brand_name or target.name
    files = {}
    if premise:
        load_preset(premise)  # validate the key before copying
        files["premise.yaml"] = (PRESET_DIR / f"{premise}.yaml").read_text()
    files |= {
        "brand_catalog.csv": BRAND_CSV,
        "competitor_catalog.csv": COMPETITOR_CSV,
        "merchandising.yaml": MERCHANDISING.replace("YOUR BRAND NAME", name),
        "buyer_behavior.template.yaml": BUYER_BEHAVIOR,
        "README.md": DIR_README.format(name=name, dir=target),
    }
    written = []
    for fname, content in files.items():
        path = target / fname
        if path.exists():
            continue
        path.write_text(content)
        written.append(fname)
    return written
