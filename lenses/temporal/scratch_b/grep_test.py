"""Qualitative look at test histories: show every turn sentence mentioning the given keywords, with the session date
and any explicit date in the sentence.  usage: grep_test.py <history_id> kw1 [kw2 ...]"""
import json
import re
import sys

hid, *kws = sys.argv[1:]
h = json.load(open(f"cache/hist/test/{hid}.json"))
SENT = re.compile(r"(?<=[.!?])\s+|\n+")
for s in h["sessions"]:
    for t in s["turns"]:
        for sent in SENT.split(t["content"]):
            low = sent.lower()
            if any(k.lower() in low for k in kws):
                print(f"{s['date'][:16]} {s['session_id']} {t['role'][:4]} | {sent.strip()[:260]}")
