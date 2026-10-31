"""Measurement wrapper (no logic of its own): the routed system (lenses/pipeline.py) with configs/best.json vs the same
config with SSA-A's round-2 proposals (ssu route -> lenses/ssa/a_handoff.py nf50a, ssa route -> a_recsent r2_conf2).
    .venv/bin/python -m harness.sweep --lens lenses/ssa/a_routed.py --variants all --split dev --tag r2-ssa-a-routed"""
from lenses.pipeline import build as _build

VARIANTS = {"best": {"config": "configs/best.json"},
            "r2a": {"config": "lenses/ssa/scratch_a/routed_r2a.json"}}


def build(q, hx, _variant: str = "", **p):
    pack = _build(q, hx, _variant=_variant, **p)
    pack.variant = _variant
    return pack
