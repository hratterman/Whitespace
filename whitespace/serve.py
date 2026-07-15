"""`whitespace serve`: a local browser workbench for the paste-seam flow.

For people who don't run Claude Code: drag data files in, see validation as
friendly cards, copy the reasoning prompt for claude.ai, paste the reply
back, and view the rendered deliverables - all on localhost, all stdlib.
The model seam stays intact: the judgment work happens on the user's Claude
subscription; this server never calls a model.
"""

from __future__ import annotations

import json
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .assemble import build_analysis
from .ingest import load_inputs
from .premise import PRESET_DIR
from .prompt import build_prompt
from .render import render
from .scaffold import init_data_dir

TEMPLATE = Path(__file__).resolve().parent / "templates" / "workbench.html"

# The only files the workbench may write into the data dir, and the only
# artifacts it may serve back out - no path from the client is ever used.
UPLOADABLE = {"brand_catalog.csv", "competitor_catalog.csv", "merchandising.yaml",
              "buyer_behavior.yaml", "taxonomy.yaml", "premise.yaml"}
SERVABLE_OUT = {"deck.html", "onepager.html", "report.md", "analysis.json", "prompt.md"}
MAX_BODY = 8 * 1024 * 1024

_FENCE = re.compile(r"```(?:json)?\s*\n(\{.*?\})\s*\n```", re.S)


def _extract_report(pasted: str) -> tuple[dict, str | None]:
    """Pull report.json (and any preceding report.md prose) out of a pasted
    Claude reply. Accepts a bare JSON object too."""
    pasted = pasted.strip()
    match = None
    for match in _FENCE.finditer(pasted):
        pass  # keep the LAST fenced json block - the reply ends with report.json
    if match:
        report = json.loads(match.group(1))
        prose = pasted[:match.start()].strip()
        prose = re.sub(r"\s*```$", "", prose).strip()
        return report, (prose if len(prose) > 200 else None)
    return json.loads(pasted), None


class WorkbenchHandler(BaseHTTPRequestHandler):
    data_dir: Path  # set by serve()

    # -- plumbing ---------------------------------------------------------
    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: dict, code: int = 200) -> None:
        self._send(code, json.dumps(payload).encode(), "application/json")

    def _body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ValueError("upload too large")
        return self.rfile.read(length)

    # -- GET ---------------------------------------------------------------
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            return self._send(200, TEMPLATE.read_bytes(), "text/html; charset=utf-8")
        if path == "/api/state":
            return self._json(self._state())
        if path == "/api/prompt":
            try:
                analysis = self._analyze()
                text = build_prompt(analysis)
                (self.data_dir / "out" / "prompt.md").write_text(text)
                return self._json({"prompt": text})
            except (FileNotFoundError, ValueError) as e:
                return self._json({"error": str(e)}, 400)
        if path.startswith("/out/"):
            name = path[len("/out/"):]
            target = self.data_dir / "out" / name
            if name in SERVABLE_OUT and target.exists():
                ctype = ("text/html; charset=utf-8" if name.endswith(".html")
                         else "text/plain; charset=utf-8")
                return self._send(200, target.read_bytes(), ctype)
        self._json({"error": "not found"}, 404)

    # -- POST ---------------------------------------------------------------
    def do_POST(self):
        try:
            if self.path == "/api/init":
                req = json.loads(self._body() or b"{}")
                premise = req.get("premise") or None
                written = init_data_dir(self.data_dir, req.get("brand") or None,
                                        None if premise in (None, "attach") else premise)
                return self._json({"written": written, **self._state()})
            if self.path == "/api/upload":
                name = self.headers.get("X-Filename", "")
                if name not in UPLOADABLE:
                    return self._json({"error": f"unsupported file name {name!r} - "
                                       f"expected one of: {', '.join(sorted(UPLOADABLE))}"}, 400)
                content = self._body().decode("utf-8-sig", errors="replace")
                self.data_dir.mkdir(parents=True, exist_ok=True)
                (self.data_dir / name).write_text(content)
                return self._json(self._state())
            if self.path == "/api/analyze":
                try:
                    analysis = self._analyze()
                except (FileNotFoundError, ValueError) as e:
                    return self._json({"error": str(e)}, 400)
                return self._json({"analysis": analysis})
            if self.path == "/api/report":
                try:
                    report, prose = _extract_report(self._body().decode("utf-8"))
                except (json.JSONDecodeError, ValueError) as e:
                    return self._json({"error": "couldn't find a valid report.json in the "
                                       f"pasted reply ({e}) - paste Claude's full response, "
                                       "or just its ```json block"}, 400)
                out = self.data_dir / "out"
                try:
                    analysis = json.loads((out / "analysis.json").read_text())
                except FileNotFoundError:
                    return self._json({"error": "run the checks step first"}, 400)
                (out / "report.json").write_text(json.dumps(report, indent=2))
                if prose:
                    (out / "report.md").write_text(prose + "\n")
                try:
                    render(analysis, report, out)
                except ValueError as e:
                    return self._json({"error": str(e)}, 400)
                return self._json({"ok": True, "hasProse": bool(prose)})
        except Exception as e:  # keep the workbench alive whatever happens
            return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
        self._json({"error": "not found"}, 404)

    # -- helpers -------------------------------------------------------------
    def _analyze(self) -> dict:
        inputs = load_inputs(self.data_dir)
        analysis = build_analysis(inputs, str(self.data_dir))
        out = self.data_dir / "out"
        out.mkdir(parents=True, exist_ok=True)
        (out / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
        return analysis

    def _state(self) -> dict:
        files = {name: (self.data_dir / name).exists() for name in UPLOADABLE}
        out = {name: (self.data_dir / "out" / name).exists() for name in SERVABLE_OUT}
        presets = []
        for p in sorted(PRESET_DIR.glob("*.yaml")):
            import yaml
            data = yaml.safe_load(p.read_text())
            presets.append({"key": data["key"], "name": data["name"],
                            "description": data["description"].strip()})
        return {"dir": str(self.data_dir), "files": files, "out": out,
                "presets": presets}


def serve(data_dir: str | Path, port: int = 8787, open_browser: bool = True) -> None:
    handler = type("Handler", (WorkbenchHandler,),
                   {"data_dir": Path(data_dir).resolve()})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"Whitespace workbench: {url}  (data dir: {data_dir})\nCtrl-C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
