"""BM25-only recall study for multi questions (no model server needed).
ALL@N: every gold session among the top-N sessions (session score = max unit score);
TALL@M: every gold turn has a unit among the top-M units."""
import re, sys, collections
from core.data import questions, gold
from core.gold_turns import gold_turns
from core.index import HistoryIndex
sys.path.insert(0, "lenses/multi")
import importlib
split = sys.argv[1] if len(sys.argv) > 1 else "dev"
mode = sys.argv[2] if len(sys.argv) > 2 else "raw"
g, gt = gold(split), gold_turns()
qfun = None
if mode != "raw":
    lens = importlib.import_module("a_tally")
    qfun = lens.make_query

Ns = [3, 5, 8, 10, 15, 20, 30]
Ms = [10, 20, 40, 60, 100]
allN = collections.Counter(); tall = collections.Counter(); n = 0
for q in questions(split):
    gg = g.get(q.question_id)
    if not gg or gg["question_type"] != "multi-session" or gg["abstain"]:
        continue
    hx = HistoryIndex.load(split, q.history_id)
    query = q.question if qfun is None else qfun(q.question)
    hits = hx.bm25(query, k=2000, roles="user")
    sess = []
    for uid, s in hits:
        sid = hx.units[uid].session_id
        if sid not in sess:
            sess.append(sid)
    G = set(gg["evidence"])
    for N in Ns:
        allN[N] += G <= set(sess[:N])
    A = set(gt.get(q.question_id, []))
    for M in Ms:
        top = {hx.units[u].turn_id for u, _ in hits[:M]}
        tall[M] += A <= top
    n += 1
print(split, mode, "n", n)
print("ALL@N  ", {N: round(allN[N] / n, 3) for N in Ns})
print("TALL@M ", {M: round(tall[M] / n, 3) for M in Ms})
