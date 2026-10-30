"""Dev temporal: question templates, and whether the gold number equals a session-date gap
(between two gold sessions, or question date minus a gold session date). usage: dev_analysis.py [split]"""
import collections
import json
import re
import sys
from datetime import datetime

split = sys.argv[1] if len(sys.argv) > 1 else "dev"
D = f"../data/{split}"
F = "%Y/%m/%d (%a) %H:%M"
qs = {json.loads(l)["question_id"]: json.loads(l) for l in open(f"{D}/questions.jsonl")}
gold = [json.loads(l) for l in open(f"{D}/gold.jsonl")]
gt = json.load(open("cache/gold_turns.json"))
tmp = [g for g in gold if g["question_type"] == "temporal-reasoning"]
print("temporal", len(tmp), "abstain", sum(g["abstain"] for g in tmp))

TEMPL = [
    ("days_between", r"how many days (?:passed |had passed |have passed |were there |was it )?between|how many days (?:apart|after|before)|days had passed since .* when"),
    ("weeks_between", r"how many weeks (?:passed |had passed )?between|how many weeks (?:after|before)"),
    ("months_between", r"how many months (?:passed |had passed )?between"),
    ("days_ago", r"how many days ago|how many days have passed since|how many days since"),
    ("weeks_ago", r"how many weeks ago|how many weeks have passed since"),
    ("months_ago", r"how many months ago|how many months have passed since"),
    ("years", r"how many years|how old"),
    ("first", r"which .* first|happened first|did i .* first|earlier"),
    ("order", r"\border\b"),
    ("duration", r"how long|how many (?:days|weeks|months) did i (?:spend|take)|how many (?:days|weeks) in total"),
    ("when", r"^when |what (?:day|date|month)"),
]


def templ(q):
    for name, p in TEMPL:
        if re.search(p, q, re.I):
            return name
    return "other"


def num(ans):
    m = re.search(r"\b(\d+)\b", ans)
    if m:
        return int(m.group(1))
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    for w, v in words.items():
        if re.search(rf"\b{w}\b", ans, re.I):
            return v
    return None


hist_cache = {}


def sess_dates(hid):
    if hid not in hist_cache:
        h = json.load(open(f"cache/hist/{split}/{hid}.json"))
        hist_cache[hid] = {s["session_id"]: datetime.strptime(s["date"], F) for s in h["sessions"]}
    return hist_cache[hid]


cnt = collections.Counter()
match = collections.Counter()
rows = []
for g in tmp:
    q = qs[g["question_id"]]
    t = templ(q["question"])
    cnt[t] += 1
    if g["abstain"]:
        continue
    n = num(g["answer"])
    sd = sess_dates(q["history_id"])
    ev = sorted(sd[s] for s in g["evidence"])
    qd = datetime.strptime(q["question_date"], F)
    ok = None
    if n is not None and t in ("days_between", "weeks_between", "months_between") and len(ev) >= 2:
        gap = (ev[-1].date() - ev[0].date()).days
        div = {"days_between": 1, "weeks_between": 7, "months_between": 30.4}[t]
        ok = any(abs(gap / div - (n + d)) < (0.5 if div > 1 else 0.01) for d in (0, 1, -1)) if div == 1 else round(gap / div) == n
        ok = ok and (abs(gap - n) <= 1 if div == 1 else True)
        rows.append((t, n, gap, ok, q["question"][:110]))
    elif n is not None and t in ("days_ago", "weeks_ago", "months_ago"):
        gaps = [(qd.date() - e.date()).days for e in ev]
        div = {"days_ago": 1, "weeks_ago": 7, "months_ago": 30.4}[t]
        ok = any((abs(gp - n) <= 1) if div == 1 else round(gp / div) == n for gp in gaps)
        rows.append((t, n, gaps, ok, q["question"][:110]))
    if ok is not None:
        match[(t, ok)] += 1
print(cnt.most_common())
print(sorted(match.items()))
for r in rows:
    if not r[3]:
        print("MISS", r)
