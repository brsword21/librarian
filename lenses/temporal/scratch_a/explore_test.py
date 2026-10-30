"""Qualitative look at test temporal questions: which sentences carry explicit dates and share words with the question."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
DATE_RE = re.compile(rf"\b(\d{{4}}-\d{{2}}-\d{{2}}|(?:{MONTHS})\.? \d{{1,2}}(?:st|nd|rd|th)?(?:,? \d{{4}})?|\d{{1,2}}(?:st|nd|rd|th)? (?:of )?(?:{MONTHS})(?:,? \d{{4}})?|\d{{1,2}}/\d{{1,2}}(?:/\d{{2,4}})?)\b")
STOP = set("how many days apart were my the and i did after was is a an of to in at for on with did his her their our me".split())
SENT = re.compile(r"(?<=[.!?])\s+|\n+")

def words(s):
    return {w for w in re.findall(r"[a-z0-9']+", s.lower()) if w not in STOP and len(w) > 2}

qs = [json.loads(l) for l in open(ROOT.parent / "data/test/questions.jsonl")]
pat = re.compile(r"how many days (apart|after)", re.I)
only = sys.argv[1] if len(sys.argv) > 1 else None
for q in qs:
    if not pat.search(q["question"]):
        continue
    if only and only not in q["question"]:
        continue
    h = json.loads((ROOT / "cache/hist/test" / f"{q['history_id']}.json").read_text())
    qw = words(q["question"])
    hits = []
    for s in h["sessions"]:
        for t in s["turns"]:
            for sent in SENT.split(t["content"]):
                ds = DATE_RE.findall(sent)
                if not ds:
                    continue
                ov = qw & words(sent)
                if len(ov) >= 1:
                    hits.append((len(ov), s["date"][:10], t["role"][0], sent.strip()[:260], sorted(ov)))
    hits.sort(key=lambda x: -x[0])
    print("=" * 100)
    print(q["question_date"][:10], q["question"])
    for h_ in hits[:8]:
        print(f"  {h_[0]} {h_[1]} {h_[2]} | {h_[3]}  {h_[4]}")
