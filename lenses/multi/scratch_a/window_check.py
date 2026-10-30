"""For multi questions with time phrases: where do gold sessions sit vs the question date, and how many sessions share the window."""
import re, sys
from core.data import questions, gold, history, parse_date
split = sys.argv[1] if len(sys.argv) > 1 else "dev"
g = gold(split)
TP = re.compile(r"\b(last|past|this|since|in|during|from|recent(ly)?|before|ago|month of|year)\b[^?]*", re.I)
for q in questions(split):
    gg = g.get(q.question_id)
    if not gg or gg["question_type"] != "multi-session" or gg["abstain"]:
        continue
    if not re.search(r"\b(last|past|this year|since|in (january|february|march|april|may|june|july|august|september|october|november|december)|month of|recently|from \w+ to|week)\b", q.question, re.I):
        continue
    h = history(split, q.history_id)
    dates = {s["session_id"]: parse_date(s["date"]) for s in h["sessions"]}
    gd = sorted((q.date - dates[e]).days for e in gg["evidence"] if e in dates)
    alld = sorted((q.date - d).days for d in dates.values())
    print(f"{q.date_str[:10]} | {q.question[:80]:80s} | gold age(days) {gd} | hist age range {alld[0]}..{alld[-1]} n={len(alld)}")
