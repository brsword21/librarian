"""grep a history for a regex; print session date, role, turn idx, snippet. Usage: grep_hist.py split hid_suffix regex [width]"""
import json, re, sys, glob
split, suf, rx = sys.argv[1], sys.argv[2], re.compile(sys.argv[3], re.I)
w = int(sys.argv[4]) if len(sys.argv) > 4 else 160
path = [p for p in glob.glob(f"cache/hist/{split}/*.json") if p.endswith(suf + ".json")][0]
h = json.load(open(path))
n = 0
for si, s in enumerate(h["sessions"]):
    for ti, t in enumerate(s["turns"]):
        for m in rx.finditer(t["content"]):
            a, b = max(0, m.start() - w), min(len(t["content"]), m.end() + w)
            print(f"[s{si:03d} {s['date'][:16]} {t['role'][:4]} t{ti}] ..{t['content'][a:b]!r}..")
            n += 1
print("hits", n, "sessions", len(h["sessions"]))
