"""Integrator merge after round 1 (do not edit the source lenses from here).

Gap questions ('how many days apart / after / before ...', 94% of test temporal questions) go to lens A
(a_calendar ftb_bm25: event-pair calendar, BM25), everything else to lens B (b_sem sem_turns9: cross-encoder, whole
question route). On the gap subset A beats B by +5.0 S on dev (29 q) and +5.3 on dev200 (5 q); B is clearly better on
the aggregate / order / 'ago' questions that A parses as single events."""
from __future__ import annotations

import re

from harness.sweep import load_lens

_GAP = re.compile(r"how many (days|weeks|months)\b.*\b(apart|after|before|between|passed)|days? (apart|after|before)", re.I)
_A = load_lens("lenses/temporal/a_calendar.py")
_B = load_lens("lenses/temporal/b_sem.py")

VARIANTS = {"gapA_semB": {"a_variant": "ftb_bm25", "b_variant": "sem_turns9"}}


def build(q, hx, _variant: str = "", a_variant: str = "ftb_bm25", b_variant: str = "sem_turns9", **_):
    use_a = bool(_GAP.search(q.question))
    lens, v = (_A, a_variant) if use_a else (_B, b_variant)
    pack = lens.build(q, hx, _variant=v, **lens.VARIANTS[v])
    pack.variant = _variant
    pack.debug = {**(pack.debug or {}), "merged_from": f"{'a_calendar' if use_a else 'b_sem'}:{v}"}
    return pack
