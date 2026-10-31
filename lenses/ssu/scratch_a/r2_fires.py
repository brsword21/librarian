"""Questions where the outlier-runner-up rule fires (s2>-6, s2-s3>3): best unit text of s1 and s2."""
import json, sys
from core.data import gold, questions
from core.index import HistoryIndex
types = sys.argv[1].split(",")
for d in sys.argv[2:]:
    split = d.rstrip("/").split("/")[-1]; g = gold(split); qm = {q.question_id: q for q in questions(split)}
    for l in open(d + "/per_question.jsonl"):
        r = json.loads(l)
        if r.get("abstain_gold") or r["type"] not in types: continue
        ss = r["debug"]["sess"] + [("x", -12)] * 3
        if not (ss[1][1] > -6 and ss[1][1] - ss[2][1] > 3): continue
        ev = set(g[r["question_id"]]["evidence"]); hx = HistoryIndex.load(split, qm[r["question_id"]].history_id)
        print(f"[{r['type']}] {r['question']}  -> {str(g[r['question_id']]['answer'])[:60]}")
        rank = r["ranking_top"]
        for s, sc in ss[:2]:
            u = next((hx.units[x] for x in rank if hx.units[x].session_id == s), None)
            print(f"   {sc:6.1f} {'G' if s in ev else ' '} {hx.sess_by_id[s]['date_str'][:10]} {(u.text[:150] if u else '?')!r}")
