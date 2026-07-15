"""Paste-seam prompt emitter.

Bundles the reasoning method, output spec, and computed analysis into one
self-contained prompt. The user runs it through the subscription frontier
model (claude.ai / Claude Code) and saves the response as report.md. This
keeps the judgment layer on the frontier model without a runtime API call.
"""

from __future__ import annotations

import json
from pathlib import Path

METHOD_DIR = Path(__file__).resolve().parent.parent / "method"

_HEADER = """\
# Category Whitespace Analysis - Reasoning Request

You are a senior category strategist. Below you have (1) the reasoning method
you must follow, (2) the output specification for the narrative deliverable,
(3) the schema for the structured judgment file, and (4) a structured
analysis object computed deterministically from the input data.

Apply the method to the analysis object and respond with TWO artifacts, in
order:

1. The complete `report.md` deliverable - Markdown, following the output
   specification exactly, starting at the title.
2. Then a fenced ```json block containing `report.json` per the report-spec
   schema - the same judgments in structured form. (Save it as
   `out/report.json` and run `python3 -m whitespace render <data-dir>` to get
   the slide deck and executive one-pager.)

Do not restate these instructions, and do not invent figures that are not in
the analysis object (derived arithmetic and clearly-labeled judgments are
fine).
"""


def build_prompt(analysis: dict) -> str:
    reasoning = (METHOD_DIR / "REASONING.md").read_text()
    output_spec = (METHOD_DIR / "OUTPUT_SPEC.md").read_text()
    report_spec = (METHOD_DIR / "REPORT_SPEC.md").read_text()
    mode = analysis["meta"]["mode"]
    return "\n\n".join([
        _HEADER,
        f"**Mode for this run: {mode}.** "
        + ("Buyer-behavior data is present; run the full diagnostic."
           if mode == "full-diagnostic" else
           "No buyer-behavior data; run the public-data analysis and do not "
           "fabricate behavioral figures."),
        "---\n\n## (1) Reasoning method\n\n" + reasoning,
        "---\n\n## (2) Output specification (report.md)\n\n" + output_spec,
        "---\n\n## (3) Structured judgment schema (report.json)\n\n" + report_spec,
        "---\n\n## (4) Analysis object\n\n```json\n"
        + json.dumps(analysis, indent=2) + "\n```",
        "Now write report.md, then the report.json block.",
    ])
