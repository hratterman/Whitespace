"""Premise loading: the frame the whitespace method runs in.

A premise defines vocabulary — the four diagnostic questions, channel labels,
presentation language — never the method. Resolution order:

  1. <data-dir>/premise.yaml            a full custom premise, or
                                        {preset: <key>} + optional overrides
  2. premises/attach.yaml               the default frame

Custom premises are first-class: the skill derives one when a user's world
doesn't match a preset, writes it into the data directory, and it travels
with the analysis like the taxonomy does.
"""

from __future__ import annotations

from pathlib import Path

import yaml

PRESET_DIR = Path(__file__).resolve().parent.parent / "premises"
DEFAULT_PRESET = "attach"

_REQUIRED_QUESTIONS = ("participation", "depth", "mix", "capture")


def _validate(premise: dict, source: str) -> dict:
    problems = []
    for field in ("key", "name", "description"):
        if not premise.get(field):
            problems.append(f"missing {field!r}")
    questions = premise.get("questions") or {}
    for q in _REQUIRED_QUESTIONS:
        if not (questions.get(q) or {}).get("label"):
            problems.append(f"questions.{q}.label missing")
    channels = premise.get("channels") or {}
    if "own_channel" not in channels:
        problems.append("channels must include own_channel (the capture math anchors on it)")
    if problems:
        raise ValueError(f"invalid premise ({source}): " + "; ".join(problems))
    return premise


def load_preset(key: str) -> dict:
    path = PRESET_DIR / f"{key}.yaml"
    if not path.exists():
        available = sorted(p.stem for p in PRESET_DIR.glob("*.yaml"))
        raise ValueError(f"unknown premise preset {key!r} (available: {', '.join(available)})")
    with open(path) as f:
        return _validate(yaml.safe_load(f), str(path))


def load_premise(data_dir: str | Path | None = None) -> dict:
    local = Path(data_dir) / "premise.yaml" if data_dir else None
    if local and local.exists():
        with open(local) as f:
            raw = yaml.safe_load(f) or {}
        if "preset" in raw:
            premise = load_preset(raw.pop("preset"))
            premise.update(raw)  # local keys override the preset's
            return _validate(premise, str(local))
        return _validate(raw, str(local))
    return load_preset(DEFAULT_PRESET)
