"""Prototype: latest own mention for 'last X I mentioned VERB' / 'X did I VERB most recently' questions."""
import json, re, sys
sys.path.insert(0, '.')
from core.data import questions
from core.index import HistoryIndex
from lenses.temporal import b_r4_last as L

split = sys.argv[1]
qs = [q for q in questions(split) if L.parse_last(q.question)]
for q in qs:
    hx = HistoryIndex.load(split, q.history_id)
    pq = L.parse_last(q.question)
    cands = L.candidates(q, hx, pq, {})
    print('=====', q.question_id, q.question, '|', pq)
    for c in sorted(cands, key=lambda c: c['key'])[-6:]:
        print(f"   {c['date']} ce={c['ce']:.2f} own={c['own']} {c['sid']} {c['sent'][:140]!r}")
    best = L.latest(cands, {})
    print('  -> LATEST', best and (best['date'], best['sid'], best['sent'][:100]))
