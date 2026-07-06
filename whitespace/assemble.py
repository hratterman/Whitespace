"""Assemble the analysis object handed to the reasoning model."""

from __future__ import annotations

from datetime import date

from . import __version__, compute
from .ingest import Inputs
from .taxonomy import apply_taxonomy, load_taxonomy


def build_analysis(inputs: Inputs, data_dir: str) -> dict:
    taxonomy = load_taxonomy(data_dir)
    all_skus = inputs.brand_catalog + [s for skus in inputs.competitor_catalogs.values()
                                       for s in skus]
    decisions = apply_taxonomy(all_skus, taxonomy)
    unmapped = [d for d in decisions if d["how"] == "unmapped"]

    all_comp_skus = [s for skus in inputs.competitor_catalogs.values() for s in skus]
    analysis = {
        "meta": {
            "brand": inputs.brand_name,
            "mode": inputs.mode,
            "generated": date.today().isoformat(),
            "tool_version": __version__,
            "taxonomy_file": taxonomy["_path"],
        },
        "buckets": {k: v["label"] for k, v in taxonomy["buckets"].items()},
        "catalog_composition": {
            "brand": compute.catalog_composition(inputs.brand_catalog),
            "competitors": {name: compute.catalog_composition(skus)
                            for name, skus in inputs.competitor_catalogs.items()},
        },
        "price_stats_by_bucket": {
            "brand": compute.price_stats(inputs.brand_catalog),
            "competitors": {name: compute.price_stats(skus)
                            for name, skus in inputs.competitor_catalogs.items()},
        },
        "comparable_price_candidates": compute.comparable_candidates(
            inputs.brand_catalog, all_comp_skus),
        "merchandising": inputs.merchandising,
        "diagnostic": None,
        "mapping_audit": {
            "decisions": decisions,
            "unmapped": unmapped,
            "note": "unmapped SKUs are excluded from catalog_share figures; the model "
                    "must resolve each (recording bucket + reason) before treating "
                    "composition as final",
        },
        "data_flags": list(inputs.data_flags),
    }

    if inputs.buyer_behavior:
        bb = inputs.buyer_behavior
        brand = bb.get("brand") or {}
        analysis["diagnostic"] = {
            "source": bb.get("source"),
            "attach": {
                "figure_type": "attach_rate",
                "brand": brand.get("attach_rate"),
                "benchmarks": {b.get("name"): b.get("attach_rate")
                               for b in bb.get("benchmarks") or []},
            },
            "spend": {
                "figure_type": "median_spend_per_buyer",
                "brand": brand.get("median_spend"),
                "benchmarks": {b.get("name"): b.get("median_spend")
                               for b in bb.get("benchmarks") or []},
            },
            "purchase_mix": compute.purchase_mix_comparison(bb),
            "channel": compute.channel_math(bb),
            "affinity": brand.get("affinity_index"),
            "affinity_note": "index, 100 = population par; only build lifestyle angles "
                             "where the base over- or at-indexes (spec §6.5)",
        }

    return analysis
