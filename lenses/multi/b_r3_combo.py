"""Lens B round 3, combination probe: lens A's sentence-level instance rescue (lenses/multi/a_r3_pin.py, credit:
multi-A) rendered without sentence trimming (A's renderer leaves a unit whole when trim == 0) + B's additive routine
hint (b_r3_full._RATE_NEW). A's file is imported, not edited; its variants are read at call time, so this follows A's
latest code.

Why: A's rescue lifts PA (dev 0.950 -> 0.967) but keeps the 240-char term-hit trim, which loses the planted
'By the way, I ...' fact sentence (scratch_b/strict.py: PA_fact 0.479 for A r2m, 0.628 for A pin, 0.950 for B ufull).
"""
from __future__ import annotations

from harness.sweep import load_lens

from lenses.multi import b_r3_full as BF

_A = {}


def _a():
    if "m" not in _A:
        _A["m"] = load_lens("lenses/multi/a_r3_pin.py")
    return _A["m"]


VARIANTS = {
    "a_r2m_full": dict(a_variant="r2m", trim=0, rate_hint=True),
    "a_g2m_full": dict(a_variant="g2m", trim=0, rate_hint=True),
    "a_r2m_full12": dict(a_variant="r2m", trim=0, rate_hint=True, budget=12000),
}


def build(q, hx, _variant: str = "", a_variant: str = "r2m", rate_hint: bool = True, **over):
    A = _a()
    P = dict(A.VARIANTS[a_variant])
    P.update(over)
    pack = A.build(q, hx, _variant=_variant, **P)
    if rate_hint and pack.hint and BF._RATE_OLD in pack.hint:
        pack.hint = pack.hint.replace(BF._RATE_OLD, BF._RATE_NEW)
    pack.variant = _variant
    pack.debug = {**(pack.debug or {}), "a_variant": a_variant}
    return pack
