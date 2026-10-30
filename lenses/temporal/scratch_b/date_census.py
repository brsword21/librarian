"""Census of explicit date formats in histories.  usage: date_census.py <split> [max_histories]"""
import collections
import glob
import json
import re
import sys

split = sys.argv[1]
mx = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
M = r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?"
PATS = {
    "iso": re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b"),
    "mdy": re.compile(rf"\b{M}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+20\d\d\b"),
    "dmy": re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{M},?\s+20\d\d\b"),
    "md_noyear": re.compile(rf"\b{M}\s+\d{{1,2}}(?:st|nd|rd|th)?\b(?!,?\s+20\d\d)"),
    "slash": re.compile(r"\b\d{1,2}/\d{1,2}/20\d\d\b"),
}
SENT = re.compile(r"(?<=[.!?])\s+|\n+")
tot = collections.Counter()
per_hist = []
role_ct = collections.Counter()
for i, f in enumerate(sorted(glob.glob(f"cache/hist/{split}/*.json"))):
    if i >= mx:
        break
    h = json.load(open(f))
    n_dated = 0
    for s in h["sessions"]:
        for t in s["turns"]:
            for sent in SENT.split(t["content"]):
                hit = False
                for k, p in PATS.items():
                    c = len(p.findall(sent))
                    tot[k] += c
                    if c and k in ("iso", "mdy", "dmy"):
                        hit = True
                if hit:
                    n_dated += 1
                    role_ct[t["role"]] += 1
    per_hist.append((h["history_id"], len(h["sessions"]), n_dated))
print(dict(tot))
print("dated sentences by role", dict(role_ct))
for r in per_hist[:20]:
    print(r)
print("mean dated sentences/history", sum(r[2] for r in per_hist) / max(1, len(per_hist)))
