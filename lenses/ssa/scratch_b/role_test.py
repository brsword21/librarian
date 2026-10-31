"""Qualitative: which TEST questions routed to ssu would role_guess flip to ssa (no gold on test)."""
import sys
from core.data import questions
from core.index import HistoryIndex
from core.router import route
sys.path.insert(0, "lenses/ssa")
from b_role import role_features, p_from_features
n = flips = 0
for q in questions("test"):
    if route(q.question)[0] != "ssu":
        continue
    hx = HistoryIndex.load("test", q.history_id)
    f = role_features(q, hx); p = p_from_features(f["d"], f["n_first"], c=-1.2)
    n += 1; flips += p >= 0.7
    if p >= 0.4:
        print(f"{'FLIP' if p >= 0.7 else '    '} p={p:.2f} d={f['d']:+.1f} nf={f['n_first']} {q.question[:90]}", flush=True)
print(n, "routed ssu,", flips, "flipped")
