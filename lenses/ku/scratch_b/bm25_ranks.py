"""BM25-only (no model server) session-rank analysis for KU on dev / dev200.
Per answerable KU question: session rank of the old and new gold session under several query forms and
session aggregations. usage: bm25_ranks.py [split]"""
import re, sys
from collections import defaultdict
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from core.data import gold, questions
from core.gold_turns import gold_turns
from core.index import HistoryIndex

split = sys.argv[1] if len(sys.argv) > 1 else "dev"
g = gold(split); gt = gold_turns()
qs = [q for q in questions(split) if g[q.question_id]["question_type"] == "knowledge-update" and not g[q.question_id]["abstain"]]

WH = re.compile(r"^(what|which|who|where|when|how (many|much|often|long)|is|are|do|does|did|have|has|am)\b", re.I)
FILLER = re.compile(r"\b(now|currently|current|right now|these days|so far|most recently|recently|still|do i|did i|have i|am i|i|me|my)\b", re.I)

def declar(q):
    s = q.strip().rstrip("?")
    s = WH.sub("", s)
    s = re.sub(r"\b(do|did|have|has|am) i\b", "I", s, flags=re.I)
    return s.strip()

def sess_rank(hx, ranked, agg="max", topn=50):
    sc = defaultdict(list)
    for r, (uid, s) in enumerate(ranked[:topn]):
        sc[hx.units[uid].session_id].append((r, s))
    if agg == "max":
        val = {sid: max(s for _, s in v) for sid, v in sc.items()}
    elif agg == "sum2":
        val = {sid: sum(sorted([s for _, s in v], reverse=True)[:2]) for sid, v in sc.items()}
    elif agg == "ndcg":  # Emergence-style: sum 1/log2(rank+2)
        import math
        val = {sid: sum(1 / math.log2(r + 2) for r, _ in v) for sid, v in sc.items()}
    order = sorted(val, key=lambda k: -val[k])
    return {sid: i for i, sid in enumerate(order)}

stats = defaultdict(lambda: defaultdict(int))
rows = []
for q in qs:
    gg = g[q.question_id]
    hx = HistoryIndex.load(split, q.history_id)
    ev = gg["evidence"]
    ev_sorted = sorted(ev, key=lambda s: hx.sess_by_id[s]["sess_idx"])
    for qname, qtext in (("raw", q.question), ("decl", declar(q.question))):
        for roles in (None, "user"):
            ranked = hx.bm25(qtext, k=200, roles=roles)
            for agg in ("max", "sum2", "ndcg"):
                sr = sess_rank(hx, ranked, agg)
                key = f"{qname}/{roles or 'all'}/{agg}"
                rk = [sr.get(s, 999) for s in ev_sorted]
                for K in (2, 3, 5, 8, 10):
                    stats[key][f"all@{K}"] += all(r < K for r in rk)
                    stats[key][f"new@{K}"] += rk[-1] < K
                if key == "raw/user/max":
                    rows.append((q.question[:70], rk, gg["answer"][:30]))
n = len(qs)
print(split, "answerable KU:", n)
for key, d in stats.items():
    print(f"{key:20s}", " ".join(f"{k}={v/n:.2f}" for k, v in d.items()))
print()
for r in rows:
    print(r)
