"""CLI: the deterministic half of the tool.

  python -m whitespace init DATA_DIR [--brand NAME]
      Scaffold a new data directory with fill-in templates.

  python -m whitespace analyze DATA_DIR [--out OUT_DIR]
      Validate inputs, compute the analysis object, write analysis.json.

  python -m whitespace prompt DATA_DIR [--out OUT_DIR]
      analyze + emit prompt.md for the paste seam.

  python -m whitespace render DATA_DIR [--out OUT_DIR]
      combine out/analysis.json + out/report.json (the model's structured
      judgment, per method/REPORT_SPEC.md) into deck.html + onepager.html.

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
from .render import render
from .scaffold import init_data_dir


def _analyze(data_dir: str, out_dir: Path) -> dict:
    inputs = load_inputs(data_dir)
    analysis = build_analysis(inputs, data_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "analysis.json"
    out_path.write_text(json.dumps(analysis, indent=2) + "\n")

    comp = analysis["catalog_composition"]
    print(f"brand: {analysis['meta']['brand']}  mode: {analysis['meta']['mode']}  "
          f"premise: {analysis['premise']['name']}")
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
    p_init = sub.add_parser("init")
    p_init.add_argument("data_dir", help="directory to scaffold")
    p_init.add_argument("--brand", default=None, help="brand name for the templates")
    p_init.add_argument("--premise", default=None,
                        help="premise preset to copy in (attach, replenishment, service, portfolio)")
    p_render = sub.add_parser("render")
    p_render.add_argument("data_dir", help="directory whose out/ holds analysis.json + report.json")
    p_render.add_argument("--out", default=None,
                          help="directory holding the json inputs and receiving the html (default: DATA_DIR/out)")
    p_serve = sub.add_parser("serve")
    p_serve.add_argument("data_dir", help="data directory to work in (created if missing)")
    p_serve.add_argument("--port", type=int, default=8787)
    p_serve.add_argument("--no-browser", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "serve":
        from .serve import serve
        serve(args.data_dir, args.port, open_browser=not args.no_browser)
        return 0
    if args.command == "render":
        out_dir = Path(args.out) if args.out else Path(args.data_dir) / "out"
        try:
            analysis = json.loads((out_dir / "analysis.json").read_text())
            report = json.loads((out_dir / "report.json").read_text())
            written = render(analysis, report, out_dir)
        except FileNotFoundError as e:
            print(f"error: {e.filename} not found — run `analyze` first, and have the "
                  "reasoning step write report.json (method/REPORT_SPEC.md)", file=sys.stderr)
            return 1
        except (ValueError, json.JSONDecodeError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        for w in written:
            print(f"wrote {w}")
        return 0
    if args.command == "init":
        written = init_data_dir(args.data_dir, args.brand, args.premise)
        if written:
            print(f"scaffolded {args.data_dir}/: {', '.join(written)}")
            print(f"\nFill in the templates (see {args.data_dir}/README.md), then run:"
                  f"\n  python3 -m whitespace analyze {args.data_dir}")
        else:
            print(f"nothing to do — all template files already exist in {args.data_dir}/")
        return 0

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
