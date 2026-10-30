"""Print every sentence with an explicit date (and optionally no-year / slash forms) in one history.
usage: dated_sents.py <split> <history_id> [--loose]"""
import json
import re
import sys

split, hid = sys.argv[1:3]
loose = "--loose" in sys.argv
M = r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?"
STRICT = re.compile(rf"\b20\d\d-\d\d-\d\d\b|\b{M}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+20\d\d\b|\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{M},?\s+20\d\d\b")
LOOSE = re.compile(rf"\b{M}\s+\d{{1,2}}(?:st|nd|rd|th)?\b|\b\d{{1,2}}/\d{{1,2}}/20\d\d\b|\b\d{{1,2}}(?:st|nd|rd|th)?\s+of\s+{M}")
SENT = re.compile(r"(?<=[.!?])\s+|\n+")
h = json.load(open(f"cache/hist/{split}/{hid}.json"))
for s in h["sessions"]:
    for t in s["turns"]:
        for sent in SENT.split(t["content"]):
            strict = STRICT.search(sent)
            if strict or (loose and LOOSE.search(sent)):
                tag = "S" if strict else "L"
                print(f"{tag} {s['date'][:16]} {t['role'][:4]} | {sent.strip()[:230]}")
