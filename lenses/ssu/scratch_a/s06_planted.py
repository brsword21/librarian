"""Case-sensitive search for insertion artifacts (planted sentences) across test histories."""
import sys, re, glob, json
sys.path.insert(0, '.')
rx = re.compile(r"\.,|[,:—-] My |—My |\b(?:and|Also,) My |\.\s*so ")
for f in sorted(glob.glob('cache/hist/test/*.json')):
    h = json.load(open(f))
    print('##', h['history_id'])
    for si, s in enumerate(h['sessions']):
        for ti, t in enumerate(s['turns']):
            if t['role'] != 'user':
                continue
            for m in rx.finditer(t['content']):
                a = max(0, m.start() - 150); b = m.end() + 120
                print(f"  [{si:3d} {s['date'][:10]} t{ti}] ...{t['content'][a:b]}...".replace('\n', ' '))
