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
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        required = {"sku_id", "name", "raw_category", "price"}
        if competitor_col:
            required.add("competitor")
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
        for i, row in enumerate(reader, start=2):
            name = (row.get("name") or "").strip()
            if not name:
                flags.append(f"{path.name} line {i}: empty name, row skipped")
                continue
            skus.append(Sku(
                sku_id=(row.get("sku_id") or "").strip() or f"{path.stem}-{i}",
                name=name,
                raw_category=(row.get("raw_category") or "").strip(),
                price=_parse_price(row.get("price", ""), f"{path.name} line {i} ({name})", flags),
                applicability=(row.get("applicability") or "").strip() or None,
                competitor=(row.get("competitor") or "").strip() or None if competitor_col else None,
            ))
    return skus


def _check_shares(mapping: dict, label: str, flags: list[str]) -> None:
    """Shares that claim to be a mix must sum to ~1.0. Flag, don't fix."""
    if not mapping:
        return
    total = sum(v for v in mapping.values() if isinstance(v, (int, float)))
    if abs(total - 1.0) > 0.02:
        flags.append(f"{label} sums to {total:.2f}, expected ~1.00 — figures reported as-supplied")


def _validate_buyer_behavior(bb: dict, flags: list[str]) -> None:
    brand = bb.get("brand") or {}
    _check_shares(brand.get("channel_capture") or {}, "brand channel_capture", flags)
    _check_shares(brand.get("purchase_mix") or {}, "brand purchase_mix (mix %, share of purchases)", flags)
    attach = brand.get("attach_rate")
    if attach is not None and not (0 <= attach <= 1):
        flags.append(f"brand attach_rate {attach} outside [0,1] — reported as-supplied")
    for bench in bb.get("benchmarks") or []:
        who = bench.get("name", "unnamed benchmark")
        _check_shares(bench.get("channel_capture") or {}, f"{who} channel_capture", flags)
        _check_shares(bench.get("purchase_mix") or {}, f"{who} purchase_mix (mix %)", flags)
    src = bb.get("source")
    if not src:
        flags.append("buyer_behavior has no `source` field — all diagnostic figures must be "
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
    comp_rows = _load_catalog_csv(comp_path, flags, competitor_col=True)

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
