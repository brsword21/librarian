"""Probe: print B.analyze sentence candidates matching a regex for one question (qualitative)."""
import re, sys
from core.data import questions
from core.index import HistoryIndex
from lenses.ku import b_r2 as R2, b_semantic as B
sp, qid, rx = sys.argv[1], sys.argv[2], sys.argv[3]
q = next(x for x in questions(sp) if x.question_id == qid)
hx = HistoryIndex.load(sp, q.history_id)
p = dict(R2.VARIANTS["r2b"])
r = B.analyze(q, hx, **p)
print(q.question, "| pair", r["pair"], "| top sess", [(s, round(r["best_by_sess"][s]["score"], 2)) for s in r["sess_rank"][:6]])
for s in sorted(r["sents"], key=lambda s: -s["score"])[:12]:
    print(f"  {s['score']:6.2f} own={s['own']:+.1f} cov={s['cov']:.2f} {hx.sess_by_id[s['sid']]['date_str'][:10]} {s['sid']} {s['raw'][:110]!r}")
print("-- regex hits in candidates:")
for s in r["sents"]:
    if re.search(rx, s["raw"], re.I):
        print(f"  {s['score']:6.2f} own={s['own']:+.1f} cov={s['cov']:.2f} {hx.sess_by_id[s['sid']]['date_str'][:10]} {s['raw'][:140]!r}")
print("-- regex hits in history (user):")
for u in hx.units:
    if u.role == "user" and re.search(rx, u.text, re.I):
        m = re.search(rx, u.text, re.I); print(f"  uid={u.uid} {u.date_str[:10]} ...{u.text[max(0,m.start()-80):m.end()+60]!r}")
