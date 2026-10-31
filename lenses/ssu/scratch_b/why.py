"""Scratch: explain b_merge's session choice on a few questions (any split, incl. test; no gold used).
    .venv/bin/python -m lenses.ssu.scratch_b.why test "cat's name" "favorite color"
"""
import re
import sys

from core.data import questions
from core.index import HistoryIndex
from lenses.ssu import b_merge
from lenses.ssu.a_owner import parse_question, unit_class
from lenses.ssu.a_struct import Q_PAST_RX, adjust, tense_adjust

split, pats = sys.argv[1], sys.argv[2:]
variant = sys.argv[-1] if sys.argv[-1] in b_merge.VARIANTS else "k11"
for q in questions(split):
    if not any(re.search(p, q.question, re.I) for p in pats):
        continue
    hx = HistoryIndex.load(split, q.history_id)
    pk = b_merge.build(q, hx, **b_merge.VARIANTS[variant])
    qp = parse_question(q.question)
    print("=" * 100)
    print(q.question, "| cite", pk.cite_plan, "| sessions", pk.debug["sessions"][:4])
    rr = dict(hx.rerank(q.question, pk.debug["ranking"]))
    for u in pk.debug["ranking"][:10]:
        U = hx.units[u]
        c = unit_class(U, qp) if U.role == "user" else None
        adj = (adjust(c, qp, b_merge._BASE) + tense_adjust(U, c, bool(Q_PAST_RX.search(q.question)), b_merge._BASE)) if c else 0
        tag = f"{c.owner}/{c.polarity}/h{int(c.head_hit)}/v{c.values[:2]}" if c else ""
        print(f"  {U.session_id} {U.role[:4]} rr={rr[u]:5.2f} adj={adj:+.2f} {tag:30s} {re.sub(chr(10),' ',U.text)[:150]}")
