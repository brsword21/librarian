"""Diagnostic: gold-session ranks on the whole-question route under several scorers (dev + dev200)."""
import json, re, math, sys
from datetime import timedelta
sys.path.insert(0, '.')
from core.data import gold, questions
from core.index import HistoryIndex
from lenses.temporal import b_evcal as E
from lenses.temporal import b_sem as B

_GAP = re.compile(r"how many (days|weeks|months)\b.*\b(apart|after|before|between|passed)|days? (apart|after|before)", re.I)
_TIME = re.compile(r"\b(?:(?:a|one|two|three|four|five|six|seven|eight|nine|ten|\d+|a couple of|a few)\s+(?:days?|weeks?|months?|years?)\s+ago"
                   r"|(?:last|past|this)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week(?:end)?|month|year)"
                   r"|on the (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|yesterday|today)\b", re.I)

def strip(q): return re.sub(r"\s+", " ", _TIME.sub(" ", q)).strip()

def ranks(hx, q, rows):
    best = {}
    for r in rows:
        best.setdefault(r['session_id'], len(best))
    return best

out = []
for split in ['dev', 'dev200']:
    G = gold(split)
    for q in questions(split):
        g = G[q.question_id]
        if g['question_type'] != 'temporal-reasoning' or g['abstain'] or _GAP.search(q.question): continue
        if E.parse_question(q.question)['events']: continue
        hx = HistoryIndex.load(split, q.history_id)
        anchor = E.question_anchor(q.question, q.date)
        res = {}
        for name, qt, wprior in [('base', q.question, 2.0), ('strip', strip(q.question), 2.0), ('noprior', q.question, 0.0), ('strip_np', strip(q.question), 0.0), ('strip_p1', strip(q.question), 1.0)]:
            pool = {i for i, _ in hx.hybrid(qt, k=60, roles='user')}
            if anchor is not None:
                lo, hi = anchor[0] - timedelta(days=3 * anchor[1] + 2), anchor[0] + timedelta(days=anchor[1] + 2)
                win = [u.uid for u in hx.units if lo <= u.date.date() <= hi]
                if win: pool |= {i for i, _ in hx.hybrid(qt, k=20, uids=win, roles='user')}
            pool = [i for i in pool if hx.units[i].date <= q.date + timedelta(days=1)]
            rows = []
            for uid, ce in hx.rerank(qt, pool):
                u = hx.units[uid]; f = ce
                if anchor is not None:
                    f += wprior * math.exp(-abs((u.date.date() - anchor[0]).days) / max(2, anchor[1]))
                rows.append({'uid': uid, 'score': f, 'ce': ce, 'session_id': u.session_id})
            rows.sort(key=lambda r: -r['score'])
            rk = ranks(hx, q, rows)
            res[name] = [rk.get(s, 99) for s in g['evidence']]
        print(split, q.question[:70], {k: sorted(v) for k, v in res.items()}, flush=True)
