"""print sessions: python show_sess.py split hid idx_or_sid [...] (turns truncated at 600 chars)"""
import json, sys
split, hid, *keys = sys.argv[1:]
h = json.load(open(f"cache/hist/{split}/{hid}.json"))
for k in keys:
    for si, s in enumerate(h["sessions"]):
        if str(si) == k or s["session_id"] == k:
            print(f"===== [{si}] {s['session_id']} {s['date']} turns={len(s['turns'])}")
            for t in s["turns"]:
                c = t["content"]
                print(f"  {t['role']}({len(c)}): {c[:600]!r}")
