"""Dev temporal: how often does the gold day count equal the gap between evidence session dates? Where does the
relative expression in the gold turn shift it?"""
import json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from core.data import gold, questions, history, parse_date  # noqa
from core.gold_turns import gold_turns  # noqa

g = gold("dev")
gt = gold_turns()
qs = [q for q in questions("dev") if g[q.question_id]["question_type"] == "temporal-reasoning"]
REL = re.compile(r"\b(today|yesterday|tonight|this morning|last (?:night|week|weekend|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
                 r"(?:a|one|two|three|four|five|six|seven|\d+|a couple of|a few) (?:days?|weeks?|months?) (?:ago|earlier|later|before)|"
                 r"(?:on |this |last )?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|just|recently|earlier today|the other day|"
                 r"(?:january|february|march|april|may|june|july|august|september|october|november|december) \d{1,2}(?:st|nd|rd|th)?|"
                 r"\d{1,2}(?:st|nd|rd|th)? of (?:january|february|march|april|may|june|july|august|september|october|november|december))\b", re.I)

ok = tot = 0
for q in qs:
    gg = g[q.question_id]
    if gg["abstain"]:
        continue
    m = re.match(r"\s*(\d+)", str(gg["answer"]))
    is_days = re.search(r"how many days", q.question, re.I)
    h = history("dev", q.history_id)
    sess = {s["session_id"]: s for s in h["sessions"]}
    ev = sorted(gg["evidence"], key=lambda s: sess[s]["date"])
    dates = [parse_date(sess[s]["date"]) for s in ev]
    turns = {t["turn_id"]: (s, t) for s in h["sessions"] for t in s["turns"]}
    if not is_days:
        continue
    tot += 1
    gold_n = int(m.group(1)) if m else None
    qd = q.date
    if re.search(r"\bago\b", q.question, re.I):
        gap = (qd.date() - dates[0].date()).days
    else:
        gap = (dates[-1].date() - dates[0].date()).days if len(dates) > 1 else None
    hit = gap is not None and gold_n is not None and gold_n <= gap <= gold_n + 1 or (gap is not None and gold_n is not None and gap == gold_n - 1)
    ok += bool(hit)
    print(("OK " if hit else "XX ") + f"gold={gold_n} gap={gap} nev={len(ev)} | {q.question[:110]}")
    if not hit:
        for tid in gt.get(q.question_id, []):
            s, t = turns[tid]
            rels = sorted({x.lower() for x in REL.findall(t["content"])})
            print(f"      {s['date'][:16]} {t['role'][0]} rel={rels} | {t['content'][:200]!r}")
print(ok, tot)
