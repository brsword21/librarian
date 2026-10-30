"""Grep a raw history for a regex; print matching turns with session date + role. Qualitative only.
usage: grep_hist.py <split> <history_id> <regex> [--all-roles] [--width N]"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
split, hid, pat = sys.argv[1:4]
roles = None if "--all-roles" in sys.argv else {"user"}
width = 500
if "--width" in sys.argv:
    width = int(sys.argv[sys.argv.index("--width") + 1])
h = json.loads((ROOT / "cache" / "hist" / split / f"{hid}.json").read_text())
rx = re.compile(pat, re.I)
for si, s in enumerate(h["sessions"]):
    for ti, t in enumerate(s["turns"]):
        if roles and t["role"] not in roles:
            continue
        for m in rx.finditer(t["content"]):
            a, b = max(0, m.start() - width // 2), m.end() + width // 2
            print(f"[{si:3d}] {s['date'][:10]} {s['session_id'][-6:]} t{ti} {t['role'][:4]}: ...{t['content'][a:b]}...".replace("\n", " "))
            break
