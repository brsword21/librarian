"""R4 audit helper: grep a test history's turns for regex terms (role, session date, snippet)."""
import json, re, sys
sys.path.insert(0, '.')
from core.index import HistoryIndex
packs = {json.loads(l)['question_id']: json.loads(l) for l in open('runs/final/v2_test_packs.jsonl')}
qid, pat = sys.argv[1], sys.argv[2]
p = packs[qid]
hx = HistoryIndex.load('test', p['history_id'])
rx = re.compile(pat, re.I)
inpack = {x['id'] for x in p['passages']}
for s in hx.sessions:
    for t in s['turns']:
        for m in rx.finditer(t['content']):
            a = max(0, m.start() - 160); b = min(len(t['content']), m.end() + 160)
            print(f"{s['date_str'][:10]} {s['session_id']}{'*' if s['session_id'] in inpack else ' '} {t['role'][:4]}: ...{t['content'][a:b]!r}")
            break
