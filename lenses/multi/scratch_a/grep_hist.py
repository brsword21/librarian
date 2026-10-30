"""usage: grep_hist.py split history_id regex [width] [roles]"""
import json, re, sys
from core.data import history
split, hid, pat = sys.argv[1], sys.argv[2], sys.argv[3]
w = int(sys.argv[4]) if len(sys.argv) > 4 else 160
roles = sys.argv[5].split(",") if len(sys.argv) > 5 else ["user", "assistant"]
h = history(split, hid)
rx = re.compile(pat, re.I)
n = 0
for si, s in enumerate(h["sessions"]):
    for ti, t in enumerate(s["turns"]):
        if t["role"] not in roles:
            continue
        for m in rx.finditer(t["content"]):
            a, b = max(0, m.start() - w), min(len(t["content"]), m.end() + w)
            print(f"[{si:3d} {s['date'][:16]} {s['session_id']} t{ti} {t['role'][:1]}] ...{t['content'][a:b]!r}")
            n += 1
print("hits", n, "sessions", len(h["sessions"]))
