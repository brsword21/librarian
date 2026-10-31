"""Qualitative: TEST questions routed to multi with p_assistant >= 0.6 (switch threshold for multi is 0.9)."""
import sys
from core.data import questions
from core.index import HistoryIndex
from core.router import route
sys.path.insert(0, "lenses/ssa")
from b_role import role_features, p_from_features
n = flips = 0
for q in questions("test"):
    if route(q.question)[0] != "multi":
        continue
    hx = HistoryIndex.load("test", q.history_id)
    f = role_features(q, hx); p = p_from_features(f["d"], f["n_first"], c=-1.2)
    n += 1; flips += p >= 0.9
    if p >= 0.5:
        print(f"{'FLIP' if p >= 0.9 else '    '} p={p:.2f} d={f['d']:+.1f} nf={f['n_first']} {q.question[:90]}", flush=True)
print(n, "routed multi,", flips, "flipped")
