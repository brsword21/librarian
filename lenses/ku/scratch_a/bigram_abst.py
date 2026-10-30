"""Abstention signal: question content bigrams that never occur (as a phrase) in the user's turns."""
import re, sys
sys.path.insert(0, '.')
from core.data import questions, gold, history
sys.path.insert(0, 'lenses/ku')
from lenses.ku.a_timeline import _STOPW, _CUE_RE

def bigrams(q):
    q = _CUE_RE.sub(' | ', q)
    ws = re.findall(r"[A-Za-z][\w&'’\-]*|\||\d+", q)
    out = []
    for a, b in zip(ws, ws[1:]):
        if '|' in (a, b) or a.lower() in _STOPW or b.lower() in _STOPW or len(a) < 3 or len(b) < 3:
            continue
        out.append((a.lower(), b.lower()))
    return out

def present(a, b, text):
    pa = re.escape(a[:-1] if a.endswith('s') and len(a) > 4 else a)
    pb = re.escape(b[:-1] if b.endswith('s') and len(b) > 4 else b)
    return re.search(rf"\b{pa}\w*\s+{pb}", text) is not None

for split in sys.argv[1:]:
    g = gold(split)
    qs = [q for q in questions(split) if q.question_id in g and g[q.question_id]['question_type'] == 'knowledge-update']
    fa = fu = na = nu = 0
    for q in qs:
        h = history(split, q.history_id)
        utext = ' '.join(t['content'] for s in h['sessions'] for t in s['turns'] if t['role'] == 'user').lower()
        miss = [f"{a} {b}" for a, b in bigrams(q.question) if not present(a, b, utext)]
        ab = g[q.question_id]['abstain']
        if ab: nu += 1; fu += bool(miss)
        else: na += 1; fa += bool(miss)
        if miss: print(('UNANS ' if ab else 'ans   ') + q.question[:80], miss)
    print(f'{split}: flagged unanswerable {fu}/{nu}, answerable {fa}/{na}')
