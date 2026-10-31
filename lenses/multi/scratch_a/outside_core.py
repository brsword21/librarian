"""Features of sessions outside the CE core (gold vs non-gold), to pick a recall rule.
    .venv/bin/python -m lenses.multi.scratch_a.outside_core dev"""
import sys
from collections import defaultdict
from core.data import questions, gold
from core.index import HistoryIndex
from lenses.multi import b_sweep as B
from lenses.multi import a_prune as AP
from lenses.multi import a_tally as T

split = sys.argv[1]
D = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
G = gold(split)
P = dict(B.VARIANTS["sweep"]); P.update(B.VARIANTS["deep8_10k"])
rows = []
for q in questions(split):
    g = G.get(q.question_id)
    if not g or g["question_type"] not in ("multi", "multi-session") or g.get("abstain"):
        continue
    hx = HistoryIndex.load(split, q.history_id)
    a = B.analyze(q.question, q.date)
    ranked, final, rr, lab, facet_top, rest, win_active = B._score_units(q, hx, a, P)
    st = AP._sess_strength(hx, rr, a, win_active, P)
    order = sorted(st, key=lambda s: -st[s])
    top = st[order[0]]
    core = set(s for s in order if st[s] >= top - D)
    first = {}
    n40 = defaultdict(int)
    for r, u in enumerate(ranked):
        sid = hx.units[u].session_id
        first.setdefault(sid, r)
        if r < 40:
            n40[sid] += 1
    qa = T.analyze(q.question, q.date)
    sess_order = []
    for u in ranked:
        sid = hx.units[u].session_id
        if sid not in sess_order:
            sess_order.append(sid)
    for i, s in enumerate(order):
        if s in core:
            continue
        lex = max((T.match_score(se, qa) for u in hx.units if u.session_id == s and u.role == "user"
                   for se in T.sentences(u.text)), default=0)
        rows.append((s in g["evidence"], q.question_id, i - len(core), top - st[s], sess_order.index(s) if s in sess_order else 99,
                     n40[s], lex, len(core)))
    missing = [s for s in g["evidence"] if s not in core]
    if missing:
        print(q.question_id, q.question[:70], "core", len(core), "missing gold:", len(missing))
print("gold outside core:")
for r in rows:
    if r[0]:
        print("  ", r)
import statistics
ng = [r for r in rows if not r[0]]
print("non-gold outside core:", len(ng))
for k, name in ((2, "pos_after_core"), (3, "gap"), (4, "sess_order"), (5, "n40"), (6, "lex")):
    gv = [r[k] for r in rows if r[0]]
    nv = [r[k] for r in ng]
    print(name, "gold mean", round(statistics.mean(gv), 2) if gv else None, "non-gold mean", round(statistics.mean(nv), 2))
import json
json.dump(rows, open(f"lenses/multi/scratch_a/outside_{split}.json", "w"))
