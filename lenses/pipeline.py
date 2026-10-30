"""The full system as one lens: router -> lens chosen per route in a config (default configs/best.json).
Sweep it on all questions to measure the routed system:  python -m harness.sweep --lens lenses/pipeline.py --split dev"""
from __future__ import annotations

import json

from core.paths import ROOT
from core.router import route

VARIANTS = {"routed": {"config": "configs/best.json"}}
_loaded: dict = {}


def _lens(path: str):
    if path not in _loaded:
        from harness.sweep import load_lens
        _loaded[path] = load_lens(path)
    return _loaded[path]


def build(q, hx, _variant: str = "", config: str = "configs/best.json", force_route: str | None = None, **_):
    cfg = json.loads((ROOT / config).read_text())
    r = force_route or route(q.question)[0]
    spec = cfg["routes"].get(r) or cfg["fallback"]
    lens = _lens(spec["lens"])
    params = {**lens.VARIANTS[spec["variant"]], **spec.get("params", {})}
    try:
        pack = lens.build(q, hx, _variant=spec["variant"], **params)
    except Exception:
        spec = cfg["fallback"]
        lens = _lens(spec["lens"])
        pack = lens.build(q, hx, _variant=spec["variant"], **{**lens.VARIANTS[spec["variant"]], **spec.get("params", {})})
    pack.route = r
    pack.debug = {**(pack.debug or {}), "lens": spec["lens"], "lens_variant": spec["variant"]}
    return pack
