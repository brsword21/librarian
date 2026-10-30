"""Offline check of the structural scorer WITHOUT the core index: a home-made BM25 over core.units stands in for
hx.bm25/hybrid. Reports gold-turn@1, gold-session@1, gold-turn in top-3 turns for: bm25(raw q), bm25(clean q),
struct only, bm25(clean)+struct fused like a_recsent.build. Usage: eval_struct.py dev|dev200 [w_struct]"""
import math, sys
from collections import Counter, defaultdict
sys.path.insert(0, '.')
from core.data import gold, questions, history
from core.gold_turns import gold_turns
from core.units import build_units
import lenses.ssa.a_recsent as L

split = sys.argv[1] if len(sys.argv) > 1 else 'dev'
W = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
G = gold(split); GT = gold_turns()

class HX:  # minimal stand-in
    def __init__(self, h):
        self.units, self.sessions = build_units(h)
        self.sess_by_id = {s['session_id']: s for s in self.sessions}
        self.split, self.history_id = split, h['history_id']
        self.docs = [L.content_stems(u.index_text) for u in self.units]
        self.df = Counter(); [self.df.update(set(d)) for d in self.docs]
        self.avg = sum(map(len, self.docs)) / len(self.docs)
        self.tf = [Counter(d) for d in self.docs]
    def bm25(self, query, k=200, roles=None):
        qt = L.content_stems(query); N = len(self.docs); out = []
        for i, (tf, d) in enumerate(zip(self.tf, self.docs)):
            if roles and self.units[i].role != roles: continue
            s = 0.0
            for t in qt:
                if t in tf:
                    idf = math.log(1 + (N - self.df[t] + .5) / (self.df[t] + .5))
                    s += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (.25 + .75 * len(d) / self.avg))
            if s > 0: out.append((i, s))
        out.sort(key=lambda x: -x[1]); return out[:k]

def evaluate(name, rank_fn):
    t1 = s1 = t3 = n = 0; fails = []
    for q in questions(split):
        g = G[q.question_id]
        if g['question_type'] != 'single-session-assistant': continue
        hx = HXS[q.history_id]
        ranking = rank_fn(q, hx)
        gt = set(GT.get(q.question_id, [])); gs = set(g['evidence'])
        turns = list(dict.fromkeys(hx.units[i].turn_id for i in ranking))
        n += 1
        t1 += bool(turns and turns[0] in gt); t3 += bool(gt & set(turns[:3]))
        s1 += bool(ranking and hx.units[ranking[0]].session_id in gs)
        if not (turns and turns[0] in gt): fails.append(q.question[:90])
    print(f"{name:22s} n={n} turn@1={t1/n:.3f} turn@3={t3/n:.3f} sess@1={s1/n:.3f}")
    return fails

HXS = {}
for q in questions(split):
    if G[q.question_id]['question_type'] == 'single-session-assistant' and q.history_id not in HXS:
        HXS[q.history_id] = HX(history(split, q.history_id))

def r_raw(q, hx): return [i for i, _ in hx.bm25(q.question)]
def r_clean(q, hx): return [i for i, _ in hx.bm25(L.retrieval_query(L.parse_question(q.question)))]
def fused(w, struct_only=False):
    def f(q, hx):
        qp = L.parse_question(q.question); query = L.retrieval_query(qp); idf = L.history_idf(hx)
        lists = [[i for i, _ in hx.bm25(query, k=60)]]
        if qp['rec_style'] or qp['role'] == 'assistant':
            lists.append([i for i, _ in hx.bm25(query, k=30, roles='assistant')])
        cand = list(dict.fromkeys(i for l in lists for i in l))
        st = {}
        for u in hx.units:
            if qp['role'] is None or u.role == qp['role'] or u.uid in cand:
                sc, ff = L.unit_struct(hx, u.uid, qp, idf)
                if sc > 0: st[u.uid] = sc
        cand = list(dict.fromkeys(cand + sorted(st, key=lambda i: -st[i])[:30]))
        rrf = Counter()
        for l in lists:
            for r, i in enumerate(l): rrf[i] += 1 / (20 + r + 1)
        mr = max(rrf.values()) if rrf else 1; ms = max(st.values(), default=1) or 1
        fin = {i: (0 if struct_only else rrf.get(i, 0) / mr) + w * st.get(i, 0) / ms for i in cand}
        return sorted(fin, key=lambda i: -fin[i])
    return f

evaluate('bm25 raw', r_raw)
evaluate('bm25 clean', r_clean)
fs = evaluate('struct only', fused(1.0, True))
ff = evaluate(f'bm25clean+struct w={W}', fused(W))
for w in (0.3, 0.6, 1.5):
    evaluate(f'bm25clean+struct w={w}', fused(w))
print('\nfails (fused):'); [print('  ', x) for x in ff[:25]]

# ---- within-session turn rank of the gold turn and chars needed (best session only)
if len(sys.argv) > 3:
    f = fused(W)
    rk = Counter(); need = []
    for q in questions(split):
        g = G[q.question_id]
        if g['question_type'] != 'single-session-assistant': continue
        hx = HXS[q.history_id]; ranking = f(q, hx)
        bs = hx.units[ranking[0]].session_id
        gt = set(GT.get(q.question_id, []))
        turns = list(dict.fromkeys(hx.units[i].turn_id for i in ranking if hx.units[i].session_id == bs))
        tl = {t['turn_id']: len(t['content']) for t in hx.sess_by_id[bs]['turns']}
        sess_chars = sum(tl.values())
        r = next((k for k, t in enumerate(turns) if t in gt), None)
        rk[r if r is None or r < 5 else '5+'] += 1
        if r is not None: need.append((sum(tl[t] for t in turns[:r + 1]), sess_chars))
    print('gold turn rank within best session:', dict(rk))
    import statistics as st
    print('chars to reach gold turn: median', st.median(n for n, _ in need), 'p90', sorted(n for n, _ in need)[int(.9 * len(need))],
          '| session chars median', st.median(s for _, s in need))
