"""Deterministic presentation renderer.

Combines analysis.json (all chart data, computed) with report.json (the
model's structured judgment, per method/REPORT_SPEC.md) into self-contained
HTML deliverables: deck.html (slide deck) and onepager.html (executive
one-pager). Templates carry the design; this module only validates the
report contract and injects the payload — no HTML is model-authored.
"""

from __future__ import annotations

import json
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

_REQUIRED = [
    ("title", lambda r: bool(r.get("title"))),
    ("why_it_matters", lambda r: bool(r.get("why_it_matters"))),
    ("diagnosis.verdict", lambda r: bool((r.get("diagnosis") or {}).get("verdict"))),
    ("diagnosis.narrative", lambda r: bool((r.get("diagnosis") or {}).get("narrative"))),
    ("composition.source", lambda r: (r.get("composition") or {}).get("source")
     in ("purchase_mix", "catalog_share")),
    ("composition.entities", lambda r: bool((r.get("composition") or {}).get("entities"))),
    ("recommendation.now", lambda r: bool((r.get("recommendation") or {}).get("now"))),
    ("next_step", lambda r: bool(r.get("next_step"))),
    ("appendix", lambda r: isinstance(r.get("appendix"), dict)),
]


def validate_report(report: dict, analysis: dict) -> list[str]:
    problems = [field for field, ok in _REQUIRED if not ok(report)]
    src = (report.get("composition") or {}).get("source")
    if src == "purchase_mix" and not (analysis.get("diagnostic") or {}).get("purchase_mix"):
        problems.append("composition.source=purchase_mix but analysis has no diagnostic data")
    flags = analysis.get("data_flags") or []
    carried = (report.get("appendix") or {}).get("data_flags")
    if flags and not carried:
        problems.append("appendix.data_flags: analysis flags exist but none were carried through")
    return problems


def render(analysis: dict, report: dict, out_dir: Path) -> list[Path]:
    problems = validate_report(report, analysis)
    if problems:
        raise ValueError("report.json does not meet method/REPORT_SPEC.md: "
                         + "; ".join(problems))
    payload = json.dumps({"analysis": analysis, "report": report},
                         ensure_ascii=False).replace("</", "<\\/")
    written = []
    for template, out_name in [("deck.html", "deck.html"),
                               ("onepager.html", "onepager.html")]:
        html = (TEMPLATE_DIR / template).read_text()
        marker = "/*__PAYLOAD__*/"
        if marker not in html:
            raise RuntimeError(f"template {template} is missing its payload marker")
        out_path = out_dir / out_name
        out_path.write_text(html.replace(marker, payload))
        written.append(out_path)
    return written
