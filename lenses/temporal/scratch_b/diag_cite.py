"""Cite-rule diagnostic on the whole-question route: CF1 for (gap, cap) grids, dev + dev200."""
import re, sys
sys.path.insert(0, '.')
from collections import defaultdict
from core.data import gold, questions
from core.index import HistoryIndex
from lenses.temporal import b_evcal as E
from lenses.temporal import b_sem as B
_GAP = re.compile(r"how many (days|weeks|months)\b.*\b(apart|after|before|between|passed)|days? (apart|after|before)", re.I)
P = dict(B.VARIANTS['sem_turns9'])
def f1(c, g):
    c, g = set(c), set(g)
    if not c or not g: return 0.0
    tp = len(c & g); 
    if not tp: return 0.0
    pr, rc = tp / len(c), tp / len(g); return 2 * pr * rc / (pr + rc)
acc = defaultdict(list); ng = []
for split in ['dev', 'dev200']:
    G = gold(split)
    for q in questions(split):
        g = G[q.question_id]
        if g['question_type'] != 'temporal-reasoning' or g['abstain'] or _GAP.search(q.question): continue
        if E.parse_question(q.question)['events']: continue
        hx = HistoryIndex.load(split, q.history_id)
        rows = B.rank_question(hx, q, P)
        n = B.expected_items(q.question)
        ng.append((len(g['evidence']), n))
        for gap in [1, 2, 3, 4, 5, 6, 8]:
            for cap in [1, 2, 3, 4, 5, 6]:
                c = B.cite_sessions(rows, gap, n if n else cap)
                acc[(split, gap, cap)].append(f1(c, g['evidence']))
        # relative-score rule: cite sessions whose best CE is > 0 (absolute)
        best = {}
        for r in rows: best.setdefault(r['session_id'], r['ce'])
        for thr in [-2, 0, 2, 4]:
            c = [s for s, v in best.items() if v >= thr] or [rows[0]['session_id']]
            acc[(split, 'abs', thr)].append(f1(c[: (n or 99)], g['evidence']))
print('gold counts', ng)
for k, v in sorted(acc.items(), key=lambda x: str(x[0])):
    print(k, len(v), round(sum(v) / len(v), 3))
