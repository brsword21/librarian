"""grep a history: python s02_grep.py <split> <history_id> <regex> [role] -> matching sentences with session idx/date/role"""
import json, sys, re
sys.path.insert(0, '.')
from core.data import history
from core.units import sentences
split, hid, pat = sys.argv[1:4]
role = sys.argv[4] if len(sys.argv) > 4 else None
rx = re.compile(pat, re.I)
h = history(split, hid)
n = 0
for si, s in enumerate(h['sessions']):
    prev = ''
    for ti, t in enumerate(s['turns']):
        if role and t['role'] != role:
            prev = t['content']; continue
        for sent in sentences(t['content']):
            if rx.search(sent):
                n += 1
                ctx = ''
                if t['role'] == 'user' and ti > 0:
                    ctx = ' || CTX: ' + sentences(prev)[-1][-160:] if sentences(prev) else ''
                print(f"[{si:3d} {s['date'][:10]} t{ti} {t['role'][0]}] {sent[:300]}{ctx if len(sent)<120 else ''}")
        prev = t['content']
print('matches', n, 'sessions', len(h['sessions']))
