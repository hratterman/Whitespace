"""Stdlib-only tests: python3 -m unittest discover -s tests"""

import json
import tempfile
import unittest
from pathlib import Path

from whitespace import compute
from whitespace.assemble import build_analysis
from whitespace.ingest import Sku, _check_shares, load_inputs
from whitespace.premise import load_premise, load_preset
from whitespace.render import render, validate_report
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


class TestFlexibleIngestion(unittest.TestCase):
    MERCH = ("brand: {name: T, bundles: false, named_packs: [], "
             "curation_level: none, bespoke: false, source: t}\ncompetitors:\n"
             "  - {name: R, bundles: false, named_packs: [], curation_level: none, "
             "bespoke: false, source: t}\n")

    def _dir(self, tmp, brand_csv, comp_csv=None):
        d = Path(tmp)
        (d / "brand_catalog.csv").write_text(brand_csv)
        (d / "competitor_catalog.csv").write_text(
            comp_csv or "competitor,sku_id,name,raw_category,price\nR,R1,Mats,Floor Mats,10\n")
        (d / "merchandising.yaml").write_text(self.MERCH)
        return d

    def test_aliased_headers_resolve_with_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._dir(tmp, "SKU,Product,Category,MSRP\nA1,Floor Mats,Floor Mats,$79\n")
            inputs = load_inputs(d)
            sku = inputs.brand_catalog[0]
            self.assertEqual((sku.sku_id, sku.name, sku.raw_category, sku.price),
                             ("A1", "Floor Mats", "Floor Mats", 79.0))
            self.assertTrue(any("'MSRP' as 'price'" in f for f in inputs.data_flags))

    def test_semicolon_delimiter_and_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._dir(tmp, "﻿name;category;price\nFloor Mats;Floor Mats;79\n")
            sku = load_inputs(d).brand_catalog[0]
            self.assertEqual((sku.name, sku.price), ("Floor Mats", 79.0))

    def test_priceless_catalog_degrades_with_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._dir(tmp, "name,category\nFloor Mats,Floor Mats\n")
            inputs = load_inputs(d)
            self.assertIsNone(inputs.brand_catalog[0].price)
            self.assertTrue(any("no price column" in f for f in inputs.data_flags))

    def test_unusable_headers_error_names_accepted_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._dir(tmp, "foo,bar\nx,y\n")
            with self.assertRaisesRegex(ValueError, "no usable column"):
                load_inputs(d)


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


class TestRender(unittest.TestCase):
    def _pair(self, example):
        d = REPO / "examples" / example
        analysis = build_analysis(load_inputs(d), str(d))
        report = json.loads((d / "sample-report.json").read_text())
        return analysis, report

    def test_both_fixture_reports_meet_spec_and_render(self):
        for example in ("meridian", "solstice"):
            analysis, report = self._pair(example)
            self.assertEqual(validate_report(report, analysis), [], example)
            with tempfile.TemporaryDirectory() as tmp:
                written = render(analysis, report, Path(tmp))
                self.assertEqual([w.name for w in written], ["deck.html", "onepager.html"])
                deck = (Path(tmp) / "deck.html").read_text()
                self.assertIn(report["title"], deck)
                self.assertNotIn("/*__PAYLOAD__*/", deck)

    def test_render_refuses_incomplete_report(self):
        analysis, report = self._pair("meridian")
        del report["next_step"]
        report["recommendation"]["now"] = []
        problems = validate_report(report, analysis)
        self.assertIn("next_step", problems)
        self.assertIn("recommendation.now", problems)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "REPORT_SPEC"):
                render(analysis, report, Path(tmp))

    def test_render_refuses_dropped_data_flags(self):
        analysis, report = self._pair("meridian")
        analysis["data_flags"] = ["something important"]
        report["appendix"]["data_flags"] = []
        self.assertTrue(any("carried through" in p
                            for p in validate_report(report, analysis)))

    def test_mix_source_requires_diagnostic(self):
        analysis, report = self._pair("solstice")   # public mode
        report["composition"]["source"] = "purchase_mix"
        self.assertTrue(any("no diagnostic data" in p
                            for p in validate_report(report, analysis)))


class TestPremise(unittest.TestCase):
    def test_presets_all_load_and_validate(self):
        for key in ("attach", "replenishment", "service", "portfolio"):
            premise = load_preset(key)
            self.assertEqual(premise["key"], key)
            self.assertIn("own_channel", premise["channels"])

    def test_default_is_attach(self):
        self.assertEqual(load_premise(None)["key"], "attach")

    def test_unknown_preset_names_available(self):
        with self.assertRaisesRegex(ValueError, "available:.*attach"):
            load_preset("nope")

    def test_local_preset_reference_with_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "premise.yaml").write_text(
                "preset: service\neyebrow: Custom eyebrow\n")
            premise = load_premise(tmp)
            self.assertEqual(premise["key"], "service")
            self.assertEqual(premise["eyebrow"], "Custom eyebrow")

    def test_invalid_custom_premise_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "premise.yaml").write_text(
                "key: x\nname: X\ndescription: d\nquestions: {}\nchannels: {web: W}\n")
            with self.assertRaisesRegex(ValueError, "own_channel"):
                load_premise(tmp)


class TestHarborlineFixture(unittest.TestCase):
    """Derived-premise fixture: custom bucket keys, custom channels."""

    def setUp(self):
        self.example = REPO / "examples" / "harborline"
        self.analysis = build_analysis(load_inputs(self.example), str(self.example))

    def test_custom_premise_travels_with_analysis(self):
        premise = self.analysis["premise"]
        self.assertEqual(premise["key"], "studio-schedule")
        self.assertEqual(premise["questions"]["depth"]["label"], "Frequency")

    def test_domain_bucket_keys_work_end_to_end(self):
        buckets = self.analysis["catalog_composition"]["brand"]["buckets"]
        self.assertIn("strength_progression", buckets)
        mix = self.analysis["diagnostic"]["purchase_mix"]["buckets"]
        self.assertIn("mind_body", mix)
        # typo cross-check runs against the custom keys, so no flags fire
        self.assertFalse(any("check for typos" in f
                             for f in self.analysis["data_flags"]))

    def test_custom_channels_flow_through(self):
        ch = self.analysis["diagnostic"]["channel"]
        self.assertIn("aggregator", ch["brand_channels"])
        self.assertAlmostEqual(ch["benchmark_gaps"][0]["capture_gap_points"], 0.19)

    def test_report_renders_with_premise_vocabulary(self):
        report = json.loads((self.example / "sample-report.json").read_text())
        self.assertEqual(validate_report(report, self.analysis), [])
        with tempfile.TemporaryDirectory() as tmp:
            render(self.analysis, report, Path(tmp))
            deck = (Path(tmp) / "deck.html").read_text()
            for label in ("Aggregator platforms", "Booking capture & aggregator leakage",
                          "Programs from the existing schedule", "Program first. Build later."):
                self.assertIn(label, deck)


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

    def test_init_with_premise_copies_preset(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = init_data_dir(Path(tmp) / "x", "X", premise="replenishment")
            self.assertIn("premise.yaml", written)
            self.assertEqual(load_premise(Path(tmp) / "x")["key"], "replenishment")

    def test_empty_scaffold_errors_helpfully(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "acme"
            init_data_dir(target)
            with self.assertRaisesRegex(ValueError, "no SKU rows yet"):
                load_inputs(target)


if __name__ == "__main__":
    unittest.main()
