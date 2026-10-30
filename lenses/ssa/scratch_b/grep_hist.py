"""grep a history: python grep_hist.py split hid regex [width]"""
import json, re, sys
split, hid, pat = sys.argv[1:4]
w = int(sys.argv[4]) if len(sys.argv) > 4 else 200
h = json.load(open(f'cache/hist/{split}/{hid}.json'))
rx = re.compile(pat, re.I)
for si, s in enumerate(h['sessions']):
    for i, t in enumerate(s['turns']):
        c = t['content']
        ms = list(rx.finditer(c))
        if ms:
            print(f"--- #{si} {s['session_id']} {s['date']} turn{i} {t['role']} len={len(c)} nturns={len(s['turns'])}")
            for m in ms[:3]:
                print('    ', c[max(0, m.start()-w):m.end()+w].replace('\n', ' '))
