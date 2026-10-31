"""Top structural candidate sentences per session for test ssa-routed questions (audit; no gold)."""
import json
from core.data import questions
from core.index import HistoryIndex
from core.router import route
from harness.sweep import load_lens
A = load_lens("lenses/ssa/a_recsent.py")
v1 = {json.loads(l)["question_id"]: json.loads(l) for l in open("runs/final/v1_test_packs.jsonl")}
for q in questions("test"):
    if route(q.question)[0] != "ssa":
        continue
    hx = HistoryIndex.load("test", q.history_id)
    qp = A.parse_question(q.question); qp["cue_floor"] = 0.7
    idf = A.history_idf(hx)
    best = {}
    for u in hx.units:
        if u.role != "assistant":
            continue
        sc, f = A.unit_struct(hx, u.uid, qp, idf)
        if sc > 0 and sc > best.get(u.session_id, (0,))[0]:
            best[u.session_id] = (sc, f.get("sentence", ""), A.rec_shape(f, qp), u.date_str)
    top = sorted(best.items(), key=lambda kv: -kv[1][0])[:3]
    cite = v1[q.question_id]["cite_plan"]
    print("==", q.question_id, q.question, "| cite", cite)
    for sid, (sc, s, shp, dt) in top:
        print(f"   {'*' if sid in cite else ' '} {sc:5.2f} shape={shp} {dt[:10]} {s[:170]}")
