"""Deterministic math. No judgment lives here.

Every share this module emits carries a figure_type so downstream reasoning
can never blend mix % with penetration % (spec §6.8):

  catalog_share   share of a brand's catalog SKUs in a bucket (sums to 1)
  purchase_mix    share of buyers' purchases in a bucket (sums to 1)
  attach_rate     share of buyers purchasing anything (the only "% of customers")
  channel_share   share of accessory purchases captured by a channel (sums to 1)
"""

from __future__ import annotations

import re
from collections import Counter
from itertools import groupby

from .ingest import Sku

# Tokens too generic to signal that two SKUs are the same item.
_STOPWORDS = {
    "the", "a", "an", "and", "for", "with", "of", "set", "kit", "pack",
    "black", "chrome", "premium", "deluxe", "oem", "genuine", "accessory",
}


def catalog_composition(skus: list[Sku]) -> dict:
    """Bucket counts and shares for one catalog. Unmapped SKUs are excluded
    from shares (they are unresolved, not zero) and reported separately."""
    mapped = [s for s in skus if s.bucket]
    counts = Counter(s.bucket for s in mapped)
    total = len(mapped)
    return {
        "figure_type": "catalog_share",
        "total_skus": len(skus),
        "mapped_skus": total,
        "unmapped_skus": len(skus) - total,
        "buckets": {
            b: {"sku_count": n, "share": round(n / total, 4) if total else 0.0}
            for b, n in sorted(counts.items(), key=lambda kv: -kv[1])
        },
    }


def price_stats(skus: list[Sku]) -> dict:
    """Median price per bucket — context for depth, not a comparison."""
    out = {}
    priced = sorted((s for s in skus if s.bucket and s.price is not None),
                    key=lambda s: s.bucket)
    for bucket, group in groupby(priced, key=lambda s: s.bucket):
        prices = sorted(s.price for s in group)
        n = len(prices)
        median = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
        out[bucket] = {"priced_skus": n, "median_price": round(median, 2),
                       "min_price": prices[0], "max_price": prices[-1]}
    return out


def _tokens(name: str) -> set[str]:
    return {t for t in re.sub(r"[^a-z0-9 ]+", " ", name.lower()).split()
            if t not in _STOPWORDS and len(t) > 1}


def comparable_candidates(brand_skus: list[Sku],
                          competitor_skus: list[Sku],
                          threshold: float = 0.45) -> list[dict]:
    """Propose like-for-like price pairs: same bucket, high name-token overlap,
    both priced. These are *candidates* — the model confirms or rejects each
    before any pricing claim is made, and the confidence score travels with
    the pair so weak matches are visible."""
    pairs = []
    for b in brand_skus:
        if not b.bucket or b.price is None:
            continue
        bt = _tokens(b.name)
        if not bt:
            continue
        for c in competitor_skus:
            if c.bucket != b.bucket or c.price is None:
                continue
            ct = _tokens(c.name)
            if not ct:
                continue
            jaccard = len(bt & ct) / len(bt | ct)
            if jaccard >= threshold:
                pairs.append({
                    "brand_sku": b.name,
                    "brand_price": b.price,
                    "competitor": c.competitor,
                    "competitor_sku": c.name,
                    "competitor_price": c.price,
                    "bucket": b.bucket,
                    "price_delta": round(b.price - c.price, 2),
                    "price_delta_pct": round((b.price - c.price) / c.price, 4)
                                       if c.price else None,
                    "match_confidence": round(jaccard, 2),
                    "status": "candidate — model must confirm comparability",
                })
    return sorted(pairs, key=lambda p: -p["match_confidence"])


def channel_math(buyer_behavior: dict) -> dict | None:
    """Leakage and capture gaps vs supplied benchmarks. Share points only —
    sizing into dollars needs volume assumptions, which are judgment."""
    brand = (buyer_behavior or {}).get("brand") or {}
    channels = brand.get("channel_capture")
    if not channels:
        return None
    own = channels.get("own_channel", 0.0)
    result = {
        "figure_type": "channel_share",
        "brand_channels": channels,
        "own_channel_capture": own,
        "leakage_total": round(1 - own, 4),
        "leakage_internet": channels.get("internet"),
        "benchmark_gaps": [],
    }
    for bench in buyer_behavior.get("benchmarks") or []:
        bc = bench.get("channel_capture") or {}
        if "own_channel" in bc:
            result["benchmark_gaps"].append({
                "benchmark": bench.get("name"),
                "benchmark_own_channel": bc["own_channel"],
                "benchmark_channels": bc,
                "capture_gap_points": round(bc["own_channel"] - own, 4),
            })
    return result


def purchase_mix_comparison(buyer_behavior: dict) -> dict | None:
    """Brand purchase mix side-by-side with each benchmark's, per bucket."""
    brand_mix = ((buyer_behavior or {}).get("brand") or {}).get("purchase_mix")
    if not brand_mix:
        return None
    rows = {}
    benches = [(b.get("name"), b.get("purchase_mix") or {})
               for b in buyer_behavior.get("benchmarks") or []]
    for bucket in sorted(set(brand_mix) | {k for _, m in benches for k in m}):
        rows[bucket] = {
            "brand": brand_mix.get(bucket),
            **{name: mix.get(bucket) for name, mix in benches},
        }
    return {"figure_type": "purchase_mix", "note": "share of purchases, sums to 1 per brand",
            "buckets": rows}
