"""Gold-turn rank inside the best session under different cheap scorers (no rerank: server is contended)."""
import sys, time, math
from collections import defaultdict
from core.data import gold, questions
from core.index import HistoryIndex
from core.gold_turns import gold_turns
from core.types import SHORT
sys.path.insert(0, "lenses/ssa")
import importlib.util
spec = importlib.util.spec_from_file_location("bs", "lenses/ssa/b_semantic.py"); bs = importlib.util.module_from_spec(spec); spec.loader.exec_module(bs)
split = sys.argv[1]
g = gold(split); GT = gold_turns()
qs = [q for q in questions(split) if q.question_id in g and SHORT[g[q.question_id]["question_type"]] == "ssa" and not g[q.question_id]["abstain"]]
res = defaultdict(list)
for q in qs:
    hx = HistoryIndex.load(split, q.history_id)
    A = set(GT[q.question_id]); G = set(g[q.question_id]["evidence"])
    cq = bs.clean_question(q.question)
    for name, fn in [("hyb", lambda: hx.hybrid(q.question, k=100, pool=300)),
                     ("hyb_clean", lambda: hx.hybrid(cq, k=100, pool=300)),
                     ("bm25", lambda: hx.bm25(q.question, k=100)),
                     ("dense", lambda: hx.dense(q.question, k=100))]:
        r = fn()
        # session = session of top-1 unit; also capped-sum session
        ss = defaultdict(float); cnt = defaultdict(int)
        for i, (u, s) in enumerate(r[:20]):
            sid = hx.units[u].session_id
            if cnt[sid] < 2: ss[sid] += 1 / math.log2(i + 2); cnt[sid] += 1
        top_s = max(ss, key=ss.get)
        sess_ok = top_s in G
        # turn order in top session: by best unit rank, assistant first? plain
        turn_rank = []
        for u, s in r:
            un = hx.units[u]
            if un.session_id == top_s and un.turn_id not in turn_rank: turn_rank.append(un.turn_id)
        gr = next((i for i, t in enumerate(turn_rank) if t in A), None)
        # chars until gold turn included (whole turns, plus preceding user turn not counted)
        sess = hx.sess_by_id[top_s]; tl = {t["turn_id"]: len(t["content"]) for t in sess["turns"]}
        need = sum(tl[t] for t in turn_rank[: (gr + 1)]) if gr is not None else None
        res[name].append((sess_ok, gr, need, sum(tl.values())))
for name, rows in res.items():
    n = len(rows); so = sum(r[0] for r in rows)
    r1 = sum(1 for r in rows if r[1] == 0); r2 = sum(1 for r in rows if r[1] is not None and r[1] <= 1); r3 = sum(1 for r in rows if r[1] is not None and r[1] <= 2)
    needs = sorted(r[2] for r in rows if r[2] is not None); sl = sorted(r[3] for r in rows)
    print(f"{name:10s} n={n} sess@1={so/n:.3f} turn@1={r1/n:.3f} @2={r2/n:.3f} @3={r3/n:.3f} miss={sum(1 for r in rows if r[1] is None)} "
          f"need p50={needs[len(needs)//2]} p90={needs[int(.9*len(needs))]} max={needs[-1]} sess p50={sl[n//2]} p90={sl[int(.9*n)]}")
