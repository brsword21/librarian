"""Offline check of the structural layer without core.index: lexical-overlap proxy for the reranker,
with vs without structure. Reports gold-session R@1 / R@3 and abstain_p separation. dev / dev200 only."""
import sys, re, importlib.util
from types import SimpleNamespace
sys.path.insert(0, '.')
from core.data import questions, gold, history
from core.units import build_units
spec = importlib.util.spec_from_file_location("a_owner", "lenses/ssu/a_owner.py")
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)

split = sys.argv[1] if len(sys.argv) > 1 else 'dev'
G = gold(split)
qs = [q for q in questions(split) if G.get(q.question_id, {}).get('question_type') == 'single-session-user']
P = dict(L.DEFAULTS)
res = {"plain": [0, 0], "struct": [0, 0], "struct_rec": [0, 0]}
n_ans = 0; abst = []
for q in qs:
    g = G[q.question_id]
    units, sessions = build_units(history(split, q.history_id))
    hx = SimpleNamespace(units=units)
    qp = L.parse_question(q.question)
    qst = {L.stem(w) for w in L.toks(q.question) if w not in L.STOP and len(w) > 2}
    user = [u for u in units if u.role == 'user']
    lex = {}
    for u in user:
        ut = {L.stem(w) for w in L.toks(u.index_text)}
        lex[u.uid] = len(qst & ut) / max(1, len(qst))
    pool = sorted(lex, key=lambda x: -lex[x])[:80]
    cls = {uid: L.unit_class(units[uid], qp) for uid in pool}
    sc = {}
    for uid in pool:
        f, b = L.struct_adjust(cls[uid], qp, P)
        sc[uid] = (lex[uid] + b) * f
    pres = L.head_presence(hx, qp)
    rank_plain = sorted(pool, key=lambda x: -lex[x])
    rank_struct = sorted(pool, key=lambda x: -sc[x])
    top = rank_struct[0]
    ap = L.abstain_prob(qp, pres, cls[top], lex[top])
    abst.append((g['abstain'], ap, q.question))
    if g['abstain']:
        continue
    n_ans += 1
    ev = set(g['evidence'])
    def sess_rank(r):
        out = []
        for uid in r:
            s = units[uid].session_id
            if s not in out: out.append(s)
        return out
    for name, r in (("plain", rank_plain), ("struct", rank_struct)):
        sr = sess_rank(r)
        res[name][0] += sr[0] in ev; res[name][1] += bool(set(sr[:3]) & ev)
        if name == "struct" and sr[0] not in ev and len(sys.argv) > 2:
            print("  MISS", q.question, '| top:', L._snip(cls[r[0]].sent, 100), cls[r[0]].owner, cls[r[0]].polarity)
print(f"{split}: {n_ans} answerable")
for k in ("plain", "struct"):
    print(f"  {k:7s} session R@1 {res[k][0]/n_ans:.3f}  R@3 {res[k][1]/n_ans:.3f}")
a = [x for x in abst if x[0]]; b = [x for x in abst if not x[0]]
print("  abstain_p on unanswerable:", [round(x[1], 2) for x in a])
import statistics
print(f"  abstain_p on answerable: mean {statistics.mean(x[1] for x in b):.3f}, >=0.5: {sum(x[1]>=0.5 for x in b)}/{len(b)}")
for x in b:
    if x[1] >= 0.5: print("    high-p answerable:", round(x[1], 2), x[2])
