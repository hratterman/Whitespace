"""Whitespace web API.

Wraps the deterministic compute layer and prompt emitter behind a small
Flask service so the tool can run from a browser.

  GET  /api/health          -> service health check
  GET  /api/example          -> example fixture data (meridian) as JSON
  POST /api/analyze          -> multipart file upload, returns analysis.json
  POST /api/prompt           -> JSON analysis object, returns paste-seam prompt
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

# Make the whitespace package importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from whitespace.assemble import build_analysis
from whitespace.ingest import load_inputs
from whitespace.prompt import build_prompt

REPO = Path(__file__).resolve().parent
EXAMPLE_DIR = REPO / "examples" / "meridian"
FRONTEND_DIR = REPO / "frontend"

app = Flask(__name__, static_folder=None)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "tool": "whitespace", "version": "0.1.0"})


@app.route("/api/example")
def example():
    """Return the example fixture files as a JSON bundle."""
    files = {}
    for name in ("brand_catalog.csv", "competitor_catalog.csv",
                 "merchandising.yaml", "buyer_behavior.yaml"):
        path = EXAMPLE_DIR / name
        if path.exists():
            files[name] = path.read_text()
    return jsonify({"files": files, "brand": "Meridian Trucks"})


def _save_uploads(files: dict, dest: Path) -> list[str]:
    """Save uploaded files to a temp dir. Returns list of saved filenames."""
    saved = []
    for field_name in ("brand_catalog", "competitor_catalog",
                       "merchandising", "buyer_behavior"):
        # accept both field names and actual filenames
        f = files.get(field_name) or files.get(f"{field_name}.csv") \
            or files.get(f"{field_name}.yaml")
        if f is None:
            continue
        filename = f.filename
        if not filename:
            filename = field_name
        dest.mkdir(parents=True, exist_ok=True)
        f.save(dest / filename)
        saved.append(filename)
    return saved


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Accept file uploads, run deterministic compute, return analysis.json."""
    if not request.files:
        return jsonify({"error": "no files uploaded"}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        saved = _save_uploads(request.files, tmp)

        if not any("brand_catalog" in s for s in saved):
            return jsonify({"error": "brand_catalog.csv is required"}), 400
        if not any("competitor_catalog" in s for s in saved):
            return jsonify({"error": "competitor_catalog.csv is required"}), 400
        if not any("merchandising" in s for s in saved):
            return jsonify({"error": "merchandising.yaml is required"}), 400

        try:
            inputs = load_inputs(tmp)
            analysis = build_analysis(inputs, str(tmp))
        except (FileNotFoundError, ValueError) as e:
            return jsonify({"error": str(e)}), 400

        return jsonify(analysis)


@app.route("/api/prompt", methods=["POST"])
def prompt():
    """Accept an analysis object, return the paste-seam prompt text."""
    analysis = request.get_json()
    if not analysis:
        return jsonify({"error": "no analysis object provided"}), 400
    try:
        prompt_text = build_prompt(analysis)
    except Exception as e:
        return jsonify({"error": f"prompt generation failed: {e}"}), 500
    return jsonify({"prompt": prompt_text})


# Serve the frontend in production
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def frontend(path):
    if path and (FRONTEND_DIR / path).exists():
        return send_from_directory(FRONTEND_DIR, path)
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return send_from_directory(FRONTEND_DIR, "index.html")
    return jsonify({"status": "running", "frontend": "not built yet"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3010))
    app.run(host="127.0.0.1", port=port, debug=False)
