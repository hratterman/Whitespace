"""CLI: the deterministic half of the tool.

  python -m whitespace analyze DATA_DIR [--out OUT_DIR]
      Validate inputs, compute the analysis object, write analysis.json.

  python -m whitespace prompt DATA_DIR [--out OUT_DIR]
      analyze + emit prompt.md for the paste seam.

The reasoning/report step runs on the subscription frontier model — via the
repo's Claude Code skill (agent mode) or by pasting prompt.md (paste seam).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .assemble import build_analysis
from .ingest import load_inputs
from .prompt import build_prompt


def _analyze(data_dir: str, out_dir: Path) -> dict:
    inputs = load_inputs(data_dir)
    analysis = build_analysis(inputs, data_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "analysis.json"
    out_path.write_text(json.dumps(analysis, indent=2) + "\n")

    comp = analysis["catalog_composition"]
    print(f"brand: {analysis['meta']['brand']}  mode: {analysis['meta']['mode']}")
    print(f"brand SKUs: {comp['brand']['total_skus']}  "
          f"competitors: {', '.join(comp['competitors']) or 'none'}")
    unmapped = analysis["mapping_audit"]["unmapped"]
    if unmapped:
        print(f"\nUNMAPPED ({len(unmapped)}) — the model must resolve these before "
              "composition is final:")
        for u in unmapped:
            who = u["competitor"] or "brand"
            print(f"  [{who}] {u['name']}  (raw category: {u['raw_category'] or '—'})")
    if analysis["data_flags"]:
        print(f"\nDATA FLAGS ({len(analysis['data_flags'])}):")
        for flag in analysis["data_flags"]:
            print(f"  - {flag}")
    print(f"\nwrote {out_path}")
    return analysis


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="whitespace", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("analyze", "prompt"):
        p = sub.add_parser(name)
        p.add_argument("data_dir", help="directory with the input files")
        p.add_argument("--out", default=None,
                       help="output directory (default: DATA_DIR/out)")

    args = parser.parse_args(argv)
    out_dir = Path(args.out) if args.out else Path(args.data_dir) / "out"
    try:
        analysis = _analyze(args.data_dir, out_dir)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.command == "prompt":
        prompt_path = out_dir / "prompt.md"
        prompt_path.write_text(build_prompt(analysis))
        print(f"wrote {prompt_path}\n\nPaste prompt.md into the subscription model "
              "(claude.ai or Claude Code) and save its response as report.md.")
    return 0
