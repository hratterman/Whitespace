"""Input loading and validation.

Data contract (all files live in one data directory):

  brand_catalog.csv            required   sku_id,name,raw_category,price,applicability
  competitor_catalog.csv       required   competitor,sku_id,name,raw_category,price
  merchandising.yaml           required   brand + per-competitor merchandising attributes
  buyer_behavior.yaml          optional   unlocks full-diagnostic mode
  taxonomy.yaml                optional   overrides the repo-root taxonomy

Every validation problem becomes a data flag, never a silent fixup. Only
malformed/missing required files raise.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Sku:
    sku_id: str
    name: str
    raw_category: str
    price: float | None
    applicability: str | None = None
    competitor: str | None = None  # None => the brand's own SKU
    bucket: str | None = None      # filled in by taxonomy.apply


@dataclass
class Inputs:
    brand_name: str
    brand_catalog: list[Sku]
    competitor_catalogs: dict[str, list[Sku]]
    merchandising: dict
    buyer_behavior: dict | None
    data_flags: list[str] = field(default_factory=list)

    @property
    def mode(self) -> str:
        return "full-diagnostic" if self.buyer_behavior else "public-data"


def _read_yaml(path: Path) -> dict:
    if path.with_suffix(".json").exists() and not path.exists():
        path = path.with_suffix(".json")
    with open(path) as f:
        if path.suffix == ".json":
            return json.load(f)
        return yaml.safe_load(f) or {}


# Real-world exports rarely use our canonical headers. First alias present
# wins; using a non-canonical alias is reported as a flag so the mapping is
# visible, never silent.
COLUMN_ALIASES = {
    "sku_id": ["sku_id", "sku", "id", "part_number", "part_no", "item_id",
               "item_number", "product_id", "product_code"],
    "name": ["name", "product", "product_name", "product_title", "title",
             "item", "item_name"],
    "raw_category": ["raw_category", "category", "product_category", "type",
                     "department", "product_type", "subcategory", "collection"],
    "price": ["price", "msrp", "price_usd", "list_price", "retail_price",
              "unit_price", "rrp"],
    "applicability": ["applicability", "fitment", "model", "models",
                      "compatibility", "applies_to", "segment"],
    "competitor": ["competitor", "competitor_name", "brand", "company",
                   "retailer", "seller"],
}


def _norm_header(h: str) -> str:
    return (h or "").strip().lstrip("﻿").lower().replace(" ", "_").replace("-", "_")


def _resolve_columns(fieldnames: list[str], filename: str,
                     flags: list[str], competitor_col: bool) -> dict[str, str]:
    """Map canonical field -> actual column name via the alias table."""
    normed = {_norm_header(f): f for f in fieldnames or []}
    resolved = {}
    for field, aliases in COLUMN_ALIASES.items():
        if field == "competitor" and not competitor_col:
            continue
        for alias in aliases:
            if alias in normed:
                resolved[field] = normed[alias]
                if alias != field:
                    flags.append(f"{filename}: using column {normed[alias]!r} as {field!r}")
                break
    missing_required = [f for f in (["name", "competitor"] if competitor_col else ["name"])
                        if f not in resolved]
    if missing_required:
        raise ValueError(
            f"{filename}: no usable column for {missing_required} "
            f"(accepted names e.g. {', '.join(COLUMN_ALIASES[missing_required[0]][:4])})")
    for field, note in [("raw_category", "every SKU will need model-side bucket resolution"),
                        ("price", "price comparison and price stats disabled")]:
        if field not in resolved:
            flags.append(f"{filename}: no {field} column found - {note}")
    return resolved


def _sniff_dialect(path: Path) -> csv.Dialect | type[csv.excel]:
    sample = path.open(encoding="utf-8-sig").read(4096)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def _parse_price(raw: str, where: str, flags: list[str]) -> float | None:
    raw = (raw or "").strip().replace("$", "").replace(",", "")
    if not raw:
        flags.append(f"missing price: {where} (excluded from price comparison)")
        return None
    try:
        price = float(raw)
    except ValueError:
        flags.append(f"unparseable price {raw!r}: {where} (excluded from price comparison)")
        return None
    if price < 0:
        flags.append(f"negative price {price}: {where} (excluded from price comparison)")
        return None
    return price


def _load_catalog_csv(path: Path, flags: list[str], competitor_col: bool) -> list[Sku]:
    skus: list[Sku] = []
    dialect = _sniff_dialect(path)
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, dialect=dialect)
        cols = _resolve_columns(reader.fieldnames, path.name, flags, competitor_col)

        def get(row: dict, field: str) -> str:
            return (row.get(cols[field]) or "").strip() if field in cols else ""

        for i, row in enumerate(reader, start=2):
            name = get(row, "name")
            if not name:
                flags.append(f"{path.name} line {i}: empty name, row skipped")
                continue
            price = None
            if "price" in cols:
                price = _parse_price(get(row, "price"), f"{path.name} line {i} ({name})", flags)
            skus.append(Sku(
                sku_id=get(row, "sku_id") or f"{path.stem}-{i}",
                name=name,
                raw_category=get(row, "raw_category"),
                price=price,
                applicability=get(row, "applicability") or None,
                competitor=get(row, "competitor") or None if competitor_col else None,
            ))
    return skus


def _check_shares(mapping: dict, label: str, flags: list[str]) -> None:
    """Shares that claim to be a mix must sum to ~1.0. Flag, don't fix."""
    if not mapping:
        return
    total = sum(v for v in mapping.values() if isinstance(v, (int, float)))
    if abs(total - 1.0) > 0.02:
        flags.append(f"{label} sums to {total:.2f}, expected ~1.00 - figures reported as-supplied")


def _validate_buyer_behavior(bb: dict, flags: list[str]) -> None:
    brand = bb.get("brand") or {}
    _check_shares(brand.get("channel_capture") or {}, "brand channel_capture", flags)
    _check_shares(brand.get("purchase_mix") or {}, "brand purchase_mix (mix %, share of purchases)", flags)
    attach = brand.get("attach_rate")
    if attach is not None and not (0 <= attach <= 1):
        flags.append(f"brand attach_rate {attach} outside [0,1] - reported as-supplied")
    for bench in bb.get("benchmarks") or []:
        who = bench.get("name", "unnamed benchmark")
        _check_shares(bench.get("channel_capture") or {}, f"{who} channel_capture", flags)
        _check_shares(bench.get("purchase_mix") or {}, f"{who} purchase_mix (mix %)", flags)
    src = bb.get("source")
    if not src:
        flags.append("buyer_behavior has no `source` field - all diagnostic figures must be "
                     "presented as unverified")


def load_inputs(data_dir: str | Path) -> Inputs:
    data_dir = Path(data_dir)
    flags: list[str] = []

    brand_path = data_dir / "brand_catalog.csv"
    comp_path = data_dir / "competitor_catalog.csv"
    merch_path = data_dir / "merchandising.yaml"
    for p in (brand_path, comp_path, merch_path):
        if not p.exists() and not p.with_suffix(".json").exists():
            raise FileNotFoundError(f"required input missing: {p}")

    brand_catalog = _load_catalog_csv(brand_path, flags, competitor_col=False)
    if not brand_catalog:
        raise ValueError(f"{brand_path} has no SKU rows yet - fill in the template "
                         "(see the data directory's README.md)")
    comp_rows = _load_catalog_csv(comp_path, flags, competitor_col=True)
    if not comp_rows:
        raise ValueError(f"{comp_path} has no SKU rows yet - competitor assortment is "
                         "required for benchmarking")

    competitor_catalogs: dict[str, list[Sku]] = {}
    for sku in comp_rows:
        if not sku.competitor:
            flags.append(f"competitor_catalog.csv: SKU {sku.name!r} has no competitor, row skipped")
            continue
        competitor_catalogs.setdefault(sku.competitor, []).append(sku)

    merchandising = _read_yaml(merch_path)
    brand_name = merchandising.get("brand", {}).get("name") or "Brand"
    merch_names = {c.get("name") for c in merchandising.get("competitors") or []}
    for comp in competitor_catalogs:
        if comp not in merch_names:
            flags.append(f"no merchandising attributes supplied for competitor {comp!r}")

    buyer_behavior = None
    bb_path = data_dir / "buyer_behavior.yaml"
    if bb_path.exists() or bb_path.with_suffix(".json").exists():
        buyer_behavior = _read_yaml(bb_path)
        _validate_buyer_behavior(buyer_behavior, flags)

    return Inputs(
        brand_name=brand_name,
        brand_catalog=brand_catalog,
        competitor_catalogs=competitor_catalogs,
        merchandising=merchandising,
        buyer_behavior=buyer_behavior,
        data_flags=flags,
    )
