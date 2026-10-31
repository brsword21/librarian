"""Facet / conjunct absence check for multi-session abstention (lens A round 1 signal, exported for any multi lens).

    from lenses.multi.a_abstain import facet_absence, combine
    pa, why = facet_absence(q.question, q.date, hx)      # 0..0.9, reasons such as 'conjunct-absent:Seattle'
    p = combine(p_other, pa)                             # noisy-OR

Signals (user text only, no models):
- a quoted title, a proper noun or a number-unit token ("30-gallon") of the question that no user turn contains
- one side of an "X and Y" conjunct with no stem in any user turn ("Hawaii and Seattle")
- the head noun pair of a phrase ("egg tarts", "chili peppers") never co-occurring in one user unit
Unanswerable multi questions usually miss exactly one facet, so each absent facet is strong evidence; a question that
matches everything gets 0. Dev: AUC 0.74 alone (a_tally bm25_tight).
"""
from __future__ import annotations

from lenses.multi import a_tally as T


def facet_absence(question: str, qdate, hx) -> tuple[float, list[str]]:
    qa = T.analyze(question, qdate)
    p, why = T.abstain_score(hx, qa, False, 1)
    return max(0.0, p - 0.05), why


def combine(p_other: float, p_facet: float, w: float = 1.0) -> float:
    """Noisy-OR of two abstention probabilities; w scales the facet signal."""
    return 1.0 - (1.0 - p_other) * (1.0 - min(0.95, w * p_facet))
