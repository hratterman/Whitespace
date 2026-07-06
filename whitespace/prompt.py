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
# Category Whitespace Analysis — Reasoning Request

You are a senior category strategist. Below you have (1) the reasoning method
you must follow, (2) the output specification for the deliverable, and (3) a
structured analysis object computed deterministically from the input data.

Apply the method to the analysis object and respond with the complete
`report.md` deliverable — Markdown only, following the output specification
exactly, starting at the title. Do not restate these instructions, do not
wrap the report in commentary, and do not invent figures that are not in the
analysis object (derived arithmetic and clearly-labeled judgments are fine).
"""


def build_prompt(analysis: dict) -> str:
    reasoning = (METHOD_DIR / "REASONING.md").read_text()
    output_spec = (METHOD_DIR / "OUTPUT_SPEC.md").read_text()
    mode = analysis["meta"]["mode"]
    return "\n\n".join([
        _HEADER,
        f"**Mode for this run: {mode}.** "
        + ("Buyer-behavior data is present; run the full diagnostic."
           if mode == "full-diagnostic" else
           "No buyer-behavior data; run the public-data analysis and do not "
           "fabricate behavioral figures."),
        "---\n\n## (1) Reasoning method\n\n" + reasoning,
        "---\n\n## (2) Output specification\n\n" + output_spec,
        "---\n\n## (3) Analysis object\n\n```json\n"
        + json.dumps(analysis, indent=2) + "\n```",
        "Now write report.md.",
    ])
