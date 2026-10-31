"""R3: where do gold instance sentences rank under sentence-level CE / dense, over ALL user sentences of the history?"""
import json, sys, time
from core.data import questions, gold
from core.index import HistoryIndex
from core.gold_turns import gold_turns
from lenses.multi import b_sweep as R1

split = sys.argv[1]
qids = sys.argv[2].split(",")
Q = {q.question_id: q for q in questions(split)}
G = gold(split)
GT = gold_turns()
rows = {json.loads(l)["question_id"]: json.loads(l) for l in open(f"runs/r2-multi-b/multi/b_tight/p08c35_aor/{split}/per_question.jsonl")}
for qid in qids:
    q = Q[qid]; hx = HistoryIndex.load(split, q.history_id)
    keep = set(rows[qid]["debug"]["keep"])
    gts = set(GT.get(qid, []))
    texts, own = [], []
    for u in hx.units:
        if u.role != "user":
            continue
        for s in R1.split_sents(u.text):
            if 20 <= len(s) <= 400 and R1._FIRST.search(s) and not s.rstrip().endswith("?"):
                texts.append(s); own.append(u)
    t = time.time()
    ce = hx.rerank_texts(q.question, texts)
    de = hx.dense_texts(q.question, texts)
    print(f"== {qid} {q.question[:90]}  n={len(texts)} {time.time()-t:.1f}s gold={G[qid]['evidence']}")
    for name, sc in (("CE", ce), ("dense", de)):
        order = sorted(range(len(texts)), key=lambda i: -sc[i])
        best_sess = {}
        for r, i in enumerate(order):
            best_sess.setdefault(own[i].session_id, (r, sc[i], i))
        sess_order = sorted(best_sess, key=lambda s: best_sess[s][0])
        print(f"  {name}: top={sc[order[0]]:.2f}")
        for k, sid in enumerate(sess_order[:25]):
            r, v, i = best_sess[sid]
            tag = ("GOLD" if sid in G[qid]["evidence"] else "    ") + (" KEEP" if sid in keep else "     ")
            print(f"   s#{k:2d} r{r:4d} {v:6.2f} {tag} {sid} {texts[i][:110]}")
        for sid in G[qid]["evidence"]:
            if sid in best_sess and sess_order.index(sid) >= 25:
                r, v, i = best_sess[sid]
                print(f"   GOLD late: s#{sess_order.index(sid)} r{r} {v:.2f} {texts[i][:110]}")
