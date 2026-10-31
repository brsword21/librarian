"""Measurement wrapper (no logic of its own): the routed system (lenses/pipeline.py) with configs/best.json (v1) vs
v1 + SSA-A round-3 role module (lenses/ssa/a_r3_role.py) on the ssu and multi route wrappers.
    .venv/bin/python -m harness.sweep --lens lenses/ssa/a_r3_routed.py --variants all --split dev --tag r3-ssa-a-routed"""
from lenses.pipeline import build as _build

VARIANTS = {"v1": {"config": "configs/best.json"},
            "r3fit": {"config": "lenses/ssa/scratch_a/r3/routed_r3fit.json"},
            "r3nh": {"config": "lenses/ssa/scratch_a/r3/routed_r3nh.json"}}


def build(q, hx, _variant: str = "", **p):
    pack = _build(q, hx, _variant=_variant, **p)
    pack.variant = _variant
    return pack
