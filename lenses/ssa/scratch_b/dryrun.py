"""End-to-end dry run of b_semantic on dev/dev200 with a FakeHX (minibm25 for bm25/dense/hybrid, bm25 as 'rerank').
Measures ATR / AC / PA proxy / chars with a crude pack renderer. Relative numbers only; real eval = harness.sweep."""
import json, re, sys, types
from collections import defaultdict
from datetime import datetime
sys.path.insert(0, '.'); sys.path.insert(0, 'lenses/ssa/scratch_b')
from minibm25 import Units, BM25, toks, ssa_questions
from core.data import history
from core.types import Unit, Passage, EvidencePack
import lenses.ssa.b_semantic as L

GT = json.load(open('cache/gold_turns.json'))
def norm(s): return re.sub(r'\W+', ' ', s.lower()).strip()

class FakeHX:
    def __init__(self, h):
        U = Units(h)
        self.sessions = h['sessions']
        self.units = [Unit(i, d['sid'], d['si'], datetime.strptime(d['date'], '%Y/%m/%d (%a) %H:%M'), d['date'], d['tid'],
                           d['ti'], d['role'], d['ci'], d['text'], d['ctx']) for i, d in enumerate(U.units)]
        self.bm = BM25([toks(u.index_text) for u in self.units])
        self._tu = defaultdict(list)
        for u in self.units: self._tu[u.turn_id].append(u.uid)
    def _rank(self, query, k, roles=None, uids=None):
        sc = self.bm.score(toks(query))
        ids = [i for i in range(len(sc)) if (roles is None or self.units[i].role in roles) and (uids is None or i in uids)]
        ids.sort(key=lambda i: -sc[i])
        return [(i, sc[i]) for i in ids[:k]]
    def bm25(self, query, k=200, roles=None): return self._rank(query, k, roles)
    def dense(self, query, k=200, roles=None, uids=None): return self._rank(query, k, roles, uids)
    def hybrid(self, query, k=100, roles=None, **kw): return self._rank(query, k, roles)
    def rerank(self, query, uids):
        sc = self.bm.score(toks(query)); return sorted(((u, sc[u]) for u in uids), key=lambda x: -x[1])
    def turn_units(self, tid): return self._tu[tid]
    def neighbors(self, uid, before=1, after=1):
        s = self.units[uid].session_id
        return [j for j in range(uid - before, uid + after + 1) if 0 <= j < len(self.units) and self.units[j].session_id == s]

def fake_build_pack(q, hx, ranked, budget=12000, window=1, order="chrono", hint="", max_sessions=None, whole_turns=False):
    sel, chars, sess = [], len(q.question) + len(hint) + 400, []
    for u in ranked:
        sid = hx.units[u].session_id
        if sid not in sess:
            if max_sessions and len(sess) >= max_sessions: continue
        add = [j for j in hx.neighbors(u, window, window) if j not in sel]
        c = sum(len(hx.units[j].text) + 12 for j in add)
        if chars + c > budget: continue
        if sid not in sess: sess.append(sid)
        sel += add; chars += c
    by = defaultdict(list)
    for j in sorted(sel): by[hx.units[j].session_id].append(j)
    ps = [Passage(sid, hx.units[js[0]].date_str, "\n".join(f"{hx.units[j].role}: {hx.units[j].text}" for j in js)) for sid, js in by.items()]
    return ps, {hx.units[j].turn_id for j in sel}, chars

pk = types.ModuleType('core.pack'); pk.build_pack = fake_build_pack; sys.modules['core.pack'] = pk

for sp in sys.argv[1].split(','):
    for var in sys.argv[2].split(','):
        n = atr = ac = pa = sr = cf = 0; chars = 0; fails = []
        for q, g in ssa_questions(sp):
            hx = FakeHX(history(sp, q.history_id))
            ep = L.build(q, hx, **L.VARIANTS[var], _variant=var)
            gts = set(GT.get(q.question_id, [])); gsid = g['evidence'][0]
            text = norm(" ".join(p.text for p in ep.passages))
            a_ok = norm(g['answer']) in text
            t_ok = gts <= ep.included_turns
            extractive = any(norm(g['answer']) in norm(t['content']) for s in hx.sessions for t in s['turns'] if t['turn_id'] in gts)
            n += 1; atr += t_ok; ac += a_ok; p_ok = t_ok and (a_ok if extractive else True); pa += p_ok
            sr += gsid in ep.session_ids(); cf += (gsid in ep.planned_citations()) * 2 / (1 + len(ep.planned_citations()))
            chars += ep.debug['chars']
            if not p_ok: fails.append((q.question_id, q.question[:90]))
        S = 100 * (0.65 * pa / n + 0.30 * cf / n - 0.05 * chars / n / 16000)
        print(f"{sp:6s} {var:9s} n={n} PA={pa/n:.3f} ATR={atr/n:.3f} AC={ac/n:.3f} SR={sr/n:.3f} CF1={cf/n:.3f} chars={chars/n:.0f} S~{S:.1f}")
        for f in fails[:4]: print("     fail", f)
