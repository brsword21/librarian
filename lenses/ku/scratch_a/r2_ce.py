"""R2: CE logits of own mentions for a few questions (split, qid-or-substring...)."""
import sys
sys.path.insert(0, '.')
from core.data import questions
from core.index import HistoryIndex
from lenses.ku import a_r2 as R, a_timeline as T
split, pats = sys.argv[1], sys.argv[2:]
for q in questions(split):
    if not any(p == q.question_id or p.lower() in q.question.lower() for p in pats):
        continue
    hx = HistoryIndex.load(split, q.history_id)
    p = dict(R.VARIANTS["e0"])
    spec, ranking, mentions, tl, dbg = T.analyse(q, hx, p)
    own = [m for m in mentions if m.owner == "self"]
    ce = hx.rerank_texts(q.question, [m.sent for m in own])
    print("=" * 80, "\n", q.question)
    best = {}
    for m, c in zip(own, ce):
        if m.session_id not in best or c > best[m.session_id][1]:
            best[m.session_id] = (m, c)
    for m, c in sorted(best.values(), key=lambda x: x[0].sort_key):
        tag = ("N" if tl.newest is m else "") + ("O" if tl.older is m else "")
        print(f"  {tag:2s} {m.date_str[:10]} ce={c:6.2f} sc={m.score:.2f} {m.role[:4]} | {m.sent[:110]}")
