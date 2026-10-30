"""Count capitalised name candidates co-occurring with a head-noun regex in user turns: sessions per name."""
import sys, re
from collections import defaultdict
sys.path.insert(0, '.')
from core.data import history
from core.units import sentences
split, hid, pat = sys.argv[1:4]
rx = re.compile(pat, re.I)
STOP = set("I I'm I've I'll I'd The A An And But So Also Hey Hi Our My We He She It They Any Can Do Is What How That This Just Thanks Thank Okay Ok Yes No Oh Ugh Between Then Now Maybe Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July August September October November December Like Well Plus Sounds".split())
h = history(split, hid)
cnt = defaultdict(set); ex = {}
for si, s in enumerate(h['sessions']):
    prev = ''
    for ti, t in enumerate(s['turns']):
        if t['role'] == 'user':
            ss = sentences(t['content'])
            for i, sent in enumerate(ss):
                ctx = sentences(prev)[-1] if (i == 0 and prev) else ''
                if rx.search(sent) or (rx.search(ctx) and i == 0):
                    for m in re.finditer(r"\b([A-Z][a-zà-ÿ]+(?:\s[A-Z][a-zà-ÿ]+)?)\b", sent):
                        w = m.group(1)
                        if w.split()[0] in STOP or m.start() == 0 and w in STOP:
                            continue
                        cnt[w].add(si); ex.setdefault(w, f"[{si}] {sent[:160]}")
        prev = t['content']
for w, ss in sorted(cnt.items(), key=lambda x: -len(x[1]))[:25]:
    print(f"{len(ss):3d} {w:20s} {sorted(ss)[:12]}  e.g. {ex[w]}")
