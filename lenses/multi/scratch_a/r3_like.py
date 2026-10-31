"""R3: can sentence-level evidence separate multi-session questions misrouted to ssu from true ssu ones?"""
import json, sys
from core.data import questions, gold
from core.index import HistoryIndex
from lenses.multi import a_r3_pin as A
from lenses.multi import b_sweep as R1

split = sys.argv[1]
Q = {q.question_id: q for q in questions(split)}
G = gold(split)
rows = [json.loads(l) for l in open(f"runs/merge2/all/pipeline/routed/{split}/per_question.jsonl")]
out = []
for r in rows:
    if r["route"] != "ssu":
        continue
    q = Q[r["question_id"]]
    hx = HistoryIndex.load(split, q.history_id)
    sb, bu, sg = A._sent_dense(q, hx, 0.05)
    best = sorted(((lst[0][0], sid, lst[0][2]) for sid, lst in sg.items()), reverse=True)
    v1, v2, v3 = (best + [(0, "", "")] * 3)[:3]
    fact2 = sum(1 for v, sid, s in best[:3] if R1._FACT.search(s))
    a = R1.analyze(q.question, q.date)
    row = dict(qid=q.question_id, t=r["type"], S=r.get("S"), PA=r.get("PA"), g1=round(v1[0] - v2[0], 3),
               g2=round(v1[0] - v3[0], 3), top=round(v1[0], 3), fact3=fact2, kind=a["kind"], nfac=len(a["facets"]),
               q=q.question[:80])
    out.append(row)
    print(json.dumps(row))
