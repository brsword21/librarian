"""How would role_guess behave on questions routed to multi / temporal / ku (dev)? Count flips by gold type."""
import sys
from collections import Counter
from core.data import gold, questions
from core.index import HistoryIndex
from core.router import route
sys.path.insert(0, "lenses/ssa")
from b_role import role_features, p_from_features
split = sys.argv[1] if len(sys.argv) > 1 else "dev"
g = gold(split); c = Counter()
for q in questions(split):
    r = route(q.question)[0]
    if r not in ("multi", "temporal", "ku"):
        continue
    hx = HistoryIndex.load(split, q.history_id)
    f = role_features(q, hx); p = p_from_features(f["d"], f["n_first"])
    t = g[q.question_id]["question_type"]
    c[(r, t, p >= 0.7)] += 1
    if p >= 0.7 or t.endswith("assistant"):
        print(f"{r:8s} {t[:14]:14s} p={p:.2f} d={f['d']:+.1f} nf={f['n_first']} {q.question[:80]}", flush=True)
for k, v in sorted(c.items()):
    print(k, v)
