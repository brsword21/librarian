"""ku rows of a routed ssu run: question, gold answer, gold sessions (date), cite, pack sessions, PA."""
import json, sys
from core.data import gold
from core.index import HistoryIndex
from core.data import questions
d = sys.argv[1]; typ = sys.argv[2] if len(sys.argv) > 2 else "ku"
split = d.rstrip("/").split("/")[-1]
g = gold(split); qm = {q.question_id: q for q in questions(split)}
for l in open(d + "/per_question.jsonl"):
    r = json.loads(l)
    if r.get("type") != typ or r.get("abstain_gold"):
        continue
    gg = g[r["question_id"]]; q = qm[r["question_id"]]
    hx = HistoryIndex.load(split, q.history_id)
    ev = gg["evidence"]
    def dd(s):
        return hx.sess_by_id[s]["date_str"][:10] if s in hx.sess_by_id else "?"
    print(f"PA={r['PA']:.0f} CF1={r['CF1']:.2f} | {r['question']} -> {str(gg.get('answer'))[:80]}")
    print(f"   gold: {[(s[-6:], dd(s)) for s in ev]}  cite: {[(s[-6:], dd(s)) for s in (r.get('cite_plan') or [])]}  pack: {[(p['id'][-6:], p['date'][:10]) for p in r['passages']]}  rec={r.get('debug',{}).get('qparse',{}).get('recency')}")
