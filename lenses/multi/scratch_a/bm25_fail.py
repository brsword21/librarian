"""Show gold sessions that raw BM25 ranks below N, with the gold turn text."""
import sys
from core.data import questions, gold, history
from core.gold_turns import gold_turns
from core.index import HistoryIndex
split = sys.argv[1]; N = int(sys.argv[2])
g, gt = gold(split), gold_turns()
for q in questions(split):
    gg = g.get(q.question_id)
    if not gg or gg["question_type"] != "multi-session" or gg["abstain"]:
        continue
    hx = HistoryIndex.load(split, q.history_id)
    hits = hx.bm25(q.question, k=3000, roles="user")
    sess = []
    for uid, s in hits:
        sid = hx.units[uid].session_id
        if sid not in sess: sess.append(sid)
    ranks = {e: (sess.index(e) if e in sess else 999) for e in gg["evidence"]}
    bad = [e for e, r in ranks.items() if r >= N]
    if not bad: continue
    print(f"\n### {q.question}  -> {str(gg['answer'])[:60]}  ranks={sorted(ranks.values())}")
    A = set(gt.get(q.question_id, []))
    for e in bad:
        for t in hx.sess_by_id[e]["turns"]:
            if t["turn_id"] in A:
                print(f"   [r{ranks[e]}] {t['content'][:260]!r}")
