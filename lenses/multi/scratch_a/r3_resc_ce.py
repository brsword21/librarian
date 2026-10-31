"""R3: sentence-CE of the rescued sentence (g2m) vs gold label; test: print for eyeballing."""
import json, sys, ast
from core.data import questions, gold
from core.index import HistoryIndex
from lenses.multi import a_r3_pin as A
from lenses.multi import b_sweep as R1

split, path = sys.argv[1], sys.argv[2]
Q = {q.question_id: q for q in questions(split)}
G = gold(split) if split != "test" else {}
for l in open(path):
    r = json.loads(l)
    d = r.get("debug") or {}
    if isinstance(d, str):
        d = ast.literal_eval(d)
    res = d.get("rescued") or []
    if not res:
        continue
    q = Q[r["question_id"]]
    hx = HistoryIndex.load(split, q.history_id)
    sb, bu, sg = A._sent_dense(q, hx)
    ev = set(G.get(q.question_id, {}).get("evidence", []))
    sents = [sg[s][0][2] for s in res if sg.get(s)]
    ce = hx.rerank_texts(q.question, sents)
    for sid, s, c in zip(res, sents, ce):
        lab = ("GOLD" if sid in ev else "----") if split != "test" else "test"
        print(f"{lab} ce={c:6.2f} fact={int(bool(R1._FACT.search(s)))} {q.question[:45]:45s} | {s[:110]}")
