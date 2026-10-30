"""Qualitative: short assistant turns containing recommendation verbs in test histories."""
import json, re, glob, sys
from collections import Counter
rx = re.compile(r"\b(recommend|suggest|try|go with|check out|I'd pick|my pick|best bet)\w*", re.I)
split = sys.argv[1] if len(sys.argv) > 1 else 'test'
maxlen = int(sys.argv[2]) if len(sys.argv) > 2 else 400
lens = Counter()
n_short_sess = 0; n_sess = 0
for f in sorted(glob.glob(f'cache/hist/{split}/*.json'))[:int(sys.argv[3]) if len(sys.argv) > 3 else 99]:
    h = json.load(open(f))
    for s in h['sessions']:
        n_sess += 1
        mx = max(len(t['content']) for t in s['turns'])
        if mx < 600: n_short_sess += 1
        for i, t in enumerate(s['turns']):
            if t['role'] == 'assistant' and len(t['content']) < maxlen and re.search(r"\b(I'd|I would|I) (recommend|suggest)", t['content']):
                print(h['history_id'], s['session_id'], i, '|', t['content'][:300].replace('\n', ' '))
print('sessions', n_sess, 'short(max turn<600)', n_short_sess)
