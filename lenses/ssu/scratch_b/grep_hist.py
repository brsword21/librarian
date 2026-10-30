"""Scratch: grep a cached history for a regex, print hits with session index/date, role, and context.

    .venv/bin/python lenses/ssu/scratch_b/grep_hist.py test h_d99a2da8f8ee "\\bcat\\b" [--role user] [--w 160]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
split, hid, pat = sys.argv[1:4]
role = sys.argv[sys.argv.index("--role") + 1] if "--role" in sys.argv else None
w = int(sys.argv[sys.argv.index("--w") + 1]) if "--w" in sys.argv else 160
h = json.loads((ROOT / "cache/hist" / split / f"{hid}.json").read_text())
rx = re.compile(pat, re.I)
n = 0
for si, s in enumerate(h["sessions"]):
    for ti, t in enumerate(s["turns"]):
        if role and t["role"] != role:
            continue
        for m in rx.finditer(t["content"]):
            a, b = max(0, m.start() - w), min(len(t["content"]), m.end() + w)
            snip = t["content"][a:b].replace("\n", " ")
            prev = s["turns"][ti - 1]["content"][-120:].replace("\n", " ") if ti else ""
            print(f"[{si:3d} {s['date'][:10]} {s['session_id']} t{ti} {t['role'][:4]} len={len(t['content'])}] ...{snip}...")
            if t["role"] == "user" and prev:
                print(f"      prev: ...{prev}")
            n += 1
            break
print(f"-- {n} hits in {len(h['sessions'])} sessions")
