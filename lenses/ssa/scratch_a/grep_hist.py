"""grep a history: python grep_hist.py split hid regex [maxctx]"""
import json, re, sys
split, hid, pat = sys.argv[1:4]
w = int(sys.argv[4]) if len(sys.argv) > 4 else 200
h = json.load(open(f"cache/hist/{split}/{hid}.json"))
rx = re.compile(pat, re.I)
for si, s in enumerate(h["sessions"]):
    for ti, t in enumerate(s["turns"]):
        for m in rx.finditer(t["content"]):
            a, b = max(0, m.start() - w), m.end() + w
            print(f"[{si} {s['session_id']} {s['date']} t{ti} {t['role']} len={len(t['content'])}] ...{t['content'][a:b]!r}")
