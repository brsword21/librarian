"""Precision of the verb-class gate on gold: candidates computed with keep=[] (no exclusion), share in gold sessions."""
import sys
from core.data import questions, gold
from core.index import HistoryIndex
from lenses.multi import a_r4_verb as L, b_sweep as R1
VAR = sys.argv[1]
for split in sys.argv[2:]:
    G = gold(split); n_q = n_f = tp = fp = 0; ex = []
    for q in questions(split):
        g = G[q.question_id]
        if g.get("question_type") != "multi-session" or g.get("abstain"):
            continue
        n_q += 1
        hx = HistoryIndex.load(split, q.history_id)
        a = R1.analyze(q.question, q.date)
        terms = a["terms"] + [w for f in a["facets"] for w in R1.content_terms(f)]
        P = dict(L.VARIANTS[VAR]); P["vc_max"] = 9
        r, u, d = L._vc_rescue(q, hx, a, terms, [], True, P)
        if r:
            n_f += 1
        ev = set(g.get("evidence") or [])
        for sid in r:
            if sid in ev: tp += 1
            else:
                fp += 1; ex.append((q.question[:70], [c for c in d["vc_cands"] if c[0] == sid][:1]))
    print(split, "multi q", n_q, "fired", n_f, "cand sessions in gold", tp, "not gold", fp)
    for e in ex[:8]: print("   FP", e)
