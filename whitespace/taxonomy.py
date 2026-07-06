"""Category-to-bucket mapping: explicit, inspectable, never a black box.

The taxonomy lives in taxonomy.yaml (repo root by default, overridable per
data directory). Deterministic rules map each SKU's raw category (then its
name) to a bucket. Anything the rules can't place lands in `unmapped` for the
model to resolve — it is never silently dumped into `other`.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .ingest import Sku

DEFAULT_TAXONOMY = Path(__file__).resolve().parent.parent / "taxonomy.yaml"


def load_taxonomy(data_dir: str | Path | None = None) -> dict:
    path = DEFAULT_TAXONOMY
    if data_dir and (Path(data_dir) / "taxonomy.yaml").exists():
        path = Path(data_dir) / "taxonomy.yaml"
    with open(path) as f:
        tax = yaml.safe_load(f)
    buckets = set(tax["buckets"])
    for raw, bucket in (tax.get("mapping", {}).get("exact") or {}).items():
        if bucket not in buckets:
            raise ValueError(f"taxonomy exact mapping {raw!r} -> unknown bucket {bucket!r}")
    for rule in tax.get("mapping", {}).get("keywords") or []:
        if rule["bucket"] not in buckets:
            raise ValueError(f"taxonomy keyword rule -> unknown bucket {rule['bucket']!r}")
    tax["_path"] = str(path)
    return tax


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower()).strip()


def _match_keywords(text: str, rules: list[dict]) -> str | None:
    words = f" {_norm(text)} "
    for rule in rules:
        for kw in rule.get("any", []):
            if f" {_norm(kw)} " in words or (len(kw) > 3 and _norm(kw) in words):
                return rule["bucket"]
    return None


def apply_taxonomy(skus: list[Sku], taxonomy: dict) -> list[dict]:
    """Assign sku.bucket in place; return the audit trail of every decision.

    Order: exact raw-category match, then keyword rules against the raw
    category, then keyword rules against the SKU name. Unmatched => bucket
    stays None and the decision is recorded as unmapped.
    """
    exact = {_norm(k): v for k, v in (taxonomy.get("mapping", {}).get("exact") or {}).items()}
    keyword_rules = taxonomy.get("mapping", {}).get("keywords") or []
    decisions = []
    for sku in skus:
        cat = _norm(sku.raw_category)
        if cat and cat in exact:
            sku.bucket, how = exact[cat], "exact-category"
        elif cat and (b := _match_keywords(sku.raw_category, keyword_rules)):
            sku.bucket, how = b, "keyword-category"
        elif b := _match_keywords(sku.name, keyword_rules):
            sku.bucket, how = b, "keyword-name"
        else:
            sku.bucket, how = None, "unmapped"
        decisions.append({
            "sku_id": sku.sku_id,
            "name": sku.name,
            "raw_category": sku.raw_category,
            "competitor": sku.competitor,
            "bucket": sku.bucket,
            "how": how,
        })
    return decisions
