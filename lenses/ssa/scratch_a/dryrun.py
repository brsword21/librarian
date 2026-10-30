"""Dry run of a_recsent.build with STUB index + STUB build_pack (core.pack not landed yet). Proxy metrics only:
ATR (gold turn included), AC (normalised gold answer substring in pack text), CF1 (cite_plan vs gold), chars.
Usage: dryrun.py dev|dev200 [variant ...]"""
import re, sys, types
from collections import defaultdict
sys.path.insert(0, '.')
from core.data import gold, questions, history
from core.gold_turns import gold_turns
from core.types import Passage
sys.argv += [] if len(sys.argv) > 1 else ['dev200']
split = sys.argv[1]
import importlib.util
if importlib.util.find_spec('core.pack') is None:
    def build_pack(q, hx, ranked, budget=12000, window=1, order='chrono', hint='', max_sessions=None, whole_turns=False):
        base = len(q.question) + len(hint) + 600
        chosen, sess, used = [], [], base
        for uid in ranked:
            for j in (hx.neighbors(uid, window, window) if window else [uid]):
                u = hx.units[j]
                if u.session_id not in sess:
                    if max_sessions and len(sess) >= max_sessions: continue
                    sess.append(u.session_id); used += 60
                if j in chosen: continue
                if used + len(u.text) + 12 > budget: continue
                chosen.append(j); used += len(u.text) + 12
        by = defaultdict(list)
        for j in sorted(chosen): by[hx.units[j].session_id].append(j)
        ps = [Passage(sid, hx.sess_by_id[sid]['date_str'], '\n'.join(f"{hx.units[j].role}: {hx.units[j].text}" for j in by[sid]))
              for sid in sorted(by, key=lambda s: hx.sess_by_id[s]['sess_idx'])]
        return ps, {hx.units[j].turn_id for j in chosen}, used
    m = types.ModuleType('core.pack'); m.build_pack = build_pack; sys.modules['core.pack'] = m
import lenses.ssa.a_recsent as L
sys.argv_saved = sys.argv; sys.argv = ['x', split]
from lenses.ssa.scratch_a import eval_struct as E  # noqa  (builds HX objects; prints its own table)
HX = E.HX
def hybrid(self, query, k=100, **kw): return self.bm25(query, k=k)
def rerank(self, query, uids): return [(u, 0.0) for u in uids]
def turn_units(self, tid):
    if not hasattr(self, '_tu'):
        self._tu = defaultdict(list); [self._tu[u.turn_id].append(u.uid) for u in self.units]
    return list(self._tu.get(tid, []))
def neighbors(self, uid, before=1, after=1):
    u = self.units[uid]; return [j for j in range(max(0, uid - before), min(len(self.units), uid + after + 1)) if self.units[j].session_id == u.session_id]
HX.hybrid, HX.rerank, HX.turn_units, HX.neighbors = hybrid, rerank, turn_units, neighbors
def norm(s): return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', s.lower())).strip()
G = gold(split); GT = gold_turns()
for var in (sys.argv_saved[2:] or list(L.VARIANTS)):
    tot = defaultdict(float); n = 0
    for q in questions(split):
        g = G[q.question_id]
        if g['question_type'] != 'single-session-assistant': continue
        hx = E.HXS[q.history_id]
        pk = L.build(q, hx, _variant=var, **L.VARIANTS[var])
        gt = set(GT.get(q.question_id, [])); gs = set(g['evidence'])
        atr = len(gt & pk.included_turns) / len(gt)
        text = norm(' '.join(p.text for p in pk.passages)); a = norm(g['answer'])
        ac = a in text
        cites = set(pk.planned_citations()); tp = len(cites & gs)
        cf1 = 2 * tp / (len(cites) + len(gs)) if cites else 0
        pa = (atr == 1) and (ac or len(a) > 40)   # long answers are abstractive: ATR only
        chars = pk.debug.get('chars', 0)
        n += 1
        for k, v in (('ATR', atr), ('AC', ac), ('CF1', cf1), ('PA', pa), ('chars', chars),
                     ('S', 100 * (0.65 * pa + 0.30 * cf1 - 0.05 * chars / 16000))):
            tot[k] += v
    print(f"{split} {var:10s} n={n} " + ' '.join(f"{k}={tot[k]/n:.3f}" if k != 'chars' else f"chars={tot[k]/n:.0f}" for k in ('S', 'PA', 'ATR', 'AC', 'CF1', 'chars')))
