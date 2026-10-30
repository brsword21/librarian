"""Scratch: abstention features per question from a b_sem run (rarest term df, in-top-3, best logit)."""
import json, re, sys
from core.data import questions
from core.index import HistoryIndex
from lenses.ssu import b_sem as B

run = sys.argv[1]
for split in ["dev", "dev200"]:
    qm = {q.question_id: q for q in questions(split)}
    for l in open(f"{run}/{split}/per_question.jsonl"):
        r = json.loads(l)
        q = qm[r["question_id"]]
        hx = HistoryIndex.load(split, q.history_id)
        df = B._df(hx)
        terms = sorted({B._stem(w) for w in B._words(q.question.split("?")[0]) if w not in B.STOP and len(w) > 2},
                       key=lambda t: df.get(t, 0))
        top = " ".join(hx.units[u].index_text.lower() for u in r["ranking_top"][:3])
        info = [(t, df.get(t, 0), bool(re.search(r"\b" + re.escape(t[:max(4, len(t))]), top))) for t in terms[:3]]
        if r["abstain_gold"] or r["abstain_p"] > 0.5 or info and info[0][1] <= 1:
            print(split, "ABST" if r["abstain_gold"] else "ans ", round(r["abstain_p"], 2), round(r["debug"]["best"], 1), info, q.question[:60])
