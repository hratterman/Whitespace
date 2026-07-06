# Category Whitespace Tool

Analyzes a brand's accessory/add-on catalog vs competitors and produces a
strategist-grade whitespace report. Deterministic math lives in the
`whitespace/` Python package; all judgment (diagnosis, benchmark selection,
packs, narrative) is done by you, following `method/REASONING.md` with output
per `method/OUTPUT_SPEC.md`. Both method files are binding.

**When the user asks for a whitespace, assortment, merchandising, or
competitor-gap analysis — or shows up with catalog data — use the
`whitespace` skill.** It handles the whole flow, including scaffolding and
converting messy input into the data contract.

Key commands:

```bash
python3 -m whitespace init  <data-dir>    # scaffold input templates
python3 -m whitespace analyze <data-dir>  # validate + compute analysis.json
python3 -m whitespace prompt  <data-dir>  # + paste-seam prompt for claude.ai users
python3 -m unittest discover -s tests     # test suite (stdlib runner)
```

Ground rules that override convenience:

- Never fabricate behavioral figures (attach/spend/mix/channel) in
  public-data mode, and never blend mix % with penetration %.
- Never silently repair user data — validation problems become flags or
  errors, and the category-to-bucket mapping stays inspectable
  (`taxonomy.yaml` + per-SKU audit trail).
- The frontier reasoning stays on the subscription (skill or paste seam) —
  do not wire an API model into the tool.

`examples/meridian/` is the synthetic demo fixture; `sample-report.md` in it
is the reference for output quality.
