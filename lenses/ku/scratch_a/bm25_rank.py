"""Where do KU gold sessions rank under plain BM25 (user-only vs all roles), session = max unit score."""
import json, re, sys, statistics
sys.path.insert(0, '.')
from core.data import gold, questions
from core.index import HistoryIndex

CUE = re.compile(r"\b(now|currently|current|these days|right now|most recently|most recent|recently|so far|still|anymore|"
                 r"previous|previously|initially|before|latest|at the moment|today)\b", re.I)
def clean(q):
    return CUE.sub(" ", q)

gt = json.load(open('cache/gold_turns.json'))
for split in sys.argv[1:] or ['dev']:
    g = gold(split); qs = {q.question_id: q for q in questions(split)}
    rows = []
    for qid, x in g.items():
        if x['question_type'] != 'knowledge-update' or x['abstain']:
            continue
        q = qs[qid]; hx = HistoryIndex.load(split, q.history_id)
        ev = x['evidence']
        newest = max(ev, key=lambda s: hx.sess_by_id[s]['date'])
        res = {}
        for name, roles in (('user', 'user'), ('all', None)):
            hits = hx.bm25(clean(q.question), k=2000, roles=roles)
            sess_rank = []
            for uid, sc in hits:
                sid = hx.units[uid].session_id
                if sid not in sess_rank:
                    sess_rank.append(sid)
            r = [sess_rank.index(s) + 1 if s in sess_rank else 999 for s in ev]
            rn = sess_rank.index(newest) + 1 if newest in sess_rank else 999
            # unit rank of gold turns
            gts = set(gt.get(qid, []))
            urank = [i + 1 for i, (uid, _) in enumerate(hits) if hx.units[uid].turn_id in gts]
            res[name] = (max(r), rn, min(urank) if urank else 999)
        rows.append((qid, len(hx.sessions), res))
    for name in ('user', 'all'):
        both = [r[2][name][0] for r in rows]; nw = [r[2][name][1] for r in rows]; ur = [r[2][name][2] for r in rows]
        print(split, name, 'n', len(rows),
              '| both-gold-sess within top k:', {k: sum(b <= k for b in both) for k in (2, 3, 5, 8, 12)},
              '| newest within:', {k: sum(b <= k for b in nw) for k in (1, 2, 3, 5)},
              '| median worst-gold rank', statistics.median(both))
    bad = [(r[0], r[2]['user']) for r in rows if r[2]['user'][0] > 5]
    print('  worst (user):', bad[:15])
