"""Stdlib-only tests: python3 -m unittest discover -s tests"""

import tempfile
import unittest
from pathlib import Path

from whitespace import compute
from whitespace.assemble import build_analysis
from whitespace.ingest import Sku, _check_shares, load_inputs
from whitespace.scaffold import init_data_dir
from whitespace.taxonomy import apply_taxonomy, load_taxonomy

REPO = Path(__file__).resolve().parent.parent
EXAMPLE = REPO / "examples" / "meridian"


def sku(name, category="", price=100.0, competitor=None, bucket=None):
    return Sku(sku_id=name, name=name, raw_category=category, price=price,
               competitor=competitor, bucket=bucket)


class TestTaxonomy(unittest.TestCase):
    def setUp(self):
        self.tax = load_taxonomy()

    def test_exact_category_beats_keywords(self):
        # "Wheel Locks" would hit the exterior "wheel" keyword; the exact
        # category mapping for Security must win.
        s = sku("Wheel Locks", "Security")
        apply_taxonomy([s], self.tax)
        self.assertEqual(s.bucket, "commodity_protection")

    def test_keyword_fallback_on_name(self):
        s = sku("Recovery Winch - 12000 lb", "Off-Road Equipment")
        apply_taxonomy([s], self.tax)
        self.assertEqual(s.bucket, "utility_cargo_towing")

    def test_unmapped_is_flagged_not_binned(self):
        s = sku("Power Tailgate Assist", "Convenience")
        decisions = apply_taxonomy([s], self.tax)
        self.assertIsNone(s.bucket)
        self.assertEqual(decisions[0]["how"], "unmapped")

    def test_rules_never_assign_other(self):
        for rule in self.tax["mapping"]["keywords"]:
            self.assertNotEqual(rule["bucket"], "other")
        self.assertNotIn("other", self.tax["mapping"]["exact"].values())


class TestCompute(unittest.TestCase):
    def test_composition_shares_sum_to_one_and_exclude_unmapped(self):
        skus = [sku("a", bucket="commodity_protection"),
                sku("b", bucket="commodity_protection"),
                sku("c", bucket="performance"),
                sku("d", bucket=None)]
        comp = compute.catalog_composition(skus)
        self.assertEqual(comp["figure_type"], "catalog_share")
        self.assertEqual(comp["unmapped_skus"], 1)
        self.assertAlmostEqual(
            sum(b["share"] for b in comp["buckets"].values()), 1.0, places=3)
        self.assertAlmostEqual(
            comp["buckets"]["commodity_protection"]["share"], 2 / 3, places=3)

    def test_comparables_require_same_bucket_and_overlap(self):
        brand = [sku("Carpet Floor Mats", bucket="commodity_protection", price=79)]
        comps = [sku("Carpet Mats", bucket="commodity_protection", price=69,
                     competitor="X"),
                 sku("Carpet Mats", bucket="lifestyle_whitespace", price=69,
                     competitor="Y"),
                 sku("Trailer Hitch", bucket="commodity_protection", price=399,
                     competitor="X")]
        pairs = compute.comparable_candidates(brand, comps)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["competitor"], "X")
        self.assertEqual(pairs[0]["price_delta"], 10.0)

    def test_channel_math_gaps(self):
        bb = {"brand": {"channel_capture": {"own_channel": 0.34, "internet": 0.44,
                                            "aftermarket_store": 0.17, "other": 0.05}},
              "benchmarks": [{"name": "N", "channel_capture": {"own_channel": 0.52}}]}
        ch = compute.channel_math(bb)
        self.assertEqual(ch["figure_type"], "channel_share")
        self.assertAlmostEqual(ch["leakage_total"], 0.66)
        self.assertAlmostEqual(ch["benchmark_gaps"][0]["capture_gap_points"], 0.18)

    def test_mix_sum_flagged_not_fixed(self):
        flags = []
        _check_shares({"a": 0.5, "b": 0.3}, "test mix", flags)
        self.assertEqual(len(flags), 1)
        self.assertIn("0.80", flags[0])


class TestEndToEnd(unittest.TestCase):
    def test_example_fixture_builds_full_mode(self):
        inputs = load_inputs(EXAMPLE)
        analysis = build_analysis(inputs, str(EXAMPLE))
        self.assertEqual(analysis["meta"]["mode"], "full-diagnostic")
        self.assertEqual(analysis["meta"]["brand"], "Meridian Trucks")
        # the fixture intentionally carries unmapped SKUs for the model
        unmapped_ids = {u["sku_id"] for u in analysis["mapping_audit"]["unmapped"]}
        self.assertEqual(unmapped_ids, {"MR-6001", "MR-6002", "MR-6003"})
        # commodity skew present on the offer side
        brand = analysis["catalog_composition"]["brand"]["buckets"]
        self.assertGreater(brand["commodity_protection"]["share"], 0.4)
        # figure types labeled through the diagnostic layer
        diag = analysis["diagnostic"]
        self.assertEqual(diag["purchase_mix"]["figure_type"], "purchase_mix")
        self.assertEqual(diag["channel"]["figure_type"], "channel_share")
        self.assertEqual(diag["attach"]["figure_type"], "attach_rate")
        # the rebranded-exhaust comparable is surfaced for the model to judge
        self.assertTrue(any(p["bucket"] == "performance"
                            for p in analysis["comparable_price_candidates"]))

    def test_typoed_mix_bucket_is_flagged(self):
        inputs = load_inputs(EXAMPLE)
        inputs.buyer_behavior["brand"]["purchase_mix"] = {"commodty_protection": 1.0}
        analysis = build_analysis(inputs, str(EXAMPLE))
        self.assertTrue(any("check for typos" in f for f in analysis["data_flags"]))

    def test_example_degrades_to_public_mode(self):
        inputs = load_inputs(EXAMPLE)
        inputs.buyer_behavior = None
        analysis = build_analysis(inputs, str(EXAMPLE))
        self.assertEqual(analysis["meta"]["mode"], "public-data")
        self.assertIsNone(analysis["diagnostic"])
        # public layer intact
        self.assertTrue(analysis["catalog_composition"]["competitors"])
        self.assertTrue(analysis["comparable_price_candidates"])


class TestSolsticeFixture(unittest.TestCase):
    """Second-domain fixture: taxonomy override + public-data mode."""

    def setUp(self):
        self.example = REPO / "examples" / "solstice"
        self.analysis = build_analysis(load_inputs(self.example), str(self.example))

    def test_local_taxonomy_overrides_root(self):
        self.assertIn("solstice", self.analysis["meta"]["taxonomy_file"])
        self.assertEqual(self.analysis["buckets"]["commodity_protection"],
                         "Consumables / Maintenance")

    def test_public_mode_with_no_buyer_file(self):
        self.assertEqual(self.analysis["meta"]["mode"], "public-data")
        self.assertIsNone(self.analysis["diagnostic"])

    def test_domain_keywords_map_coffee_gear(self):
        unmapped = {u["sku_id"] for u in self.analysis["mapping_audit"]["unmapped"]}
        self.assertEqual(unmapped, {"SE-20"})  # Smart Shot Timer only
        brand = self.analysis["catalog_composition"]["brand"]["buckets"]
        self.assertGreater(brand["commodity_protection"]["share"], 0.4)

    def test_exact_category_beats_performance_keyword(self):
        # "Custom Engraved Portafilter Handle" contains the performance
        # keyword "portafilter"; its Machine Customization category must win.
        decision = next(d for d in self.analysis["mapping_audit"]["decisions"]
                        if d["sku_id"] == "BC-06")
        self.assertEqual(decision["bucket"], "exterior_personalization")
        self.assertEqual(decision["how"], "exact-category")

    def test_cross_domain_comparables_found(self):
        pairs = {(p["brand_sku"], p["competitor_sku"])
                 for p in self.analysis["comparable_price_candidates"]}
        self.assertIn(("Bottomless Portafilter 58mm", "Bottomless Portafilter 58mm"),
                      pairs)


class TestScaffold(unittest.TestCase):
    def test_init_writes_templates_without_activating_full_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = init_data_dir(Path(tmp) / "acme", "Acme Bikes")
            self.assertIn("brand_catalog.csv", written)
            # the buyer template must NOT be named buyer_behavior.yaml,
            # or a fresh scaffold would claim full-diagnostic mode
            self.assertNotIn("buyer_behavior.yaml", written)
            self.assertIn("buyer_behavior.template.yaml", written)

    def test_init_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "acme"
            init_data_dir(target)
            (target / "brand_catalog.csv").write_text("user data")
            self.assertEqual(init_data_dir(target), [])
            self.assertEqual((target / "brand_catalog.csv").read_text(), "user data")

    def test_empty_scaffold_errors_helpfully(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "acme"
            init_data_dir(target)
            with self.assertRaisesRegex(ValueError, "no SKU rows yet"):
                load_inputs(target)


if __name__ == "__main__":
    unittest.main()
