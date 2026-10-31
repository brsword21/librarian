"""Measurement wrapper (no logic of its own): the routed system (lenses/pipeline.py) with configs/best_v2.json (v2)
vs v2 + SSA-A round-4 role module (lenses/ssa/a_r4_role.py) on the ssu route wrapper only.
    .venv/bin/python -m harness.sweep --lens lenses/ssa/a_r4_routed.py --variants all --split dev --tag r4-ssa-a"""
from lenses.pipeline import build as _build

VARIANTS = {"v2": {"config": "configs/best_v2.json"},
            "r4role": {"config": "lenses/ssa/scratch_a/r4/routed_r4role.json"},
            "r4rp": {"config": "lenses/ssa/scratch_a/r4/routed_r4rp.json"}}


def build(q, hx, _variant: str = "", **p):
    pack = _build(q, hx, _variant=_variant, **p)
    pack.variant = _variant
    return pack
