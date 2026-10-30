"""Qualitative audit (test, no gold): top-3 structural sentences per 'you recommended' test question. Not for tuning."""
import json, re, sys
sys.path.insert(0, '.')
from core.data import history, questions
from core.units import build_units
import lenses.ssa.a_recsent as L

class HX:
    def __init__(self, h):
        self.units, self.sessions = build_units(h)
        self.sess_by_id = {s['session_id']: s for s in self.sessions}
        self.split, self.history_id = 'test', h['history_id']
cache = {}
for q in questions('test'):
    if not re.search(r'\byou (recommend|suggest)', q.question, re.I): continue
    hx = cache.get(q.history_id) or cache.setdefault(q.history_id, HX(history('test', q.history_id)))
    qp = L.parse_question(q.question); idf = L.history_idf(hx)
    sc = []
    for u in hx.units:
        if u.role != 'assistant': continue
        s, f = L.unit_struct(hx, u.uid, qp, idf)
        if s > 0: sc.append((s, u.sess_idx, f))
    sc.sort(key=lambda x: -x[0])
    print('\n##', q.question, '| abstain_p', L.abstain_estimate(qp, {'feat': sc[0][2]} if sc else None))
    for s, si, f in sc[:3]:
        print(f'   {s:5.2f} [{si}] cue={f["cue"]} 3rd={f["third"]} con={f["contra"]} :: {f["sentence"][:150]}')
