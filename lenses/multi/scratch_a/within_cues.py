"""Inside gold sessions: how do gold user turns differ from the other user turns? (dev, dev200)"""
import re, sys, collections
from core.data import questions, gold, history
from core.gold_turns import gold_turns
CUES = {
  "btw": re.compile(r"\b(by the way|btw|oh,? and|also,|speaking of|random\b|before I forget)", re.I),
  "fact": re.compile(r"\bI(?:'ve| have| had)? (?:just |recently |also |finally |actually |already )?(?:\w+ed|got|bought|went|took|made|saw|had|did|ran|swam|rode|read|ate|met|won|lost|spent|paid|sold|gave|built|began|started|finished|wrote|drove|flew|brought|caught|found|kept|left|sent|set|paid)\b", re.I),
  "num": re.compile(r"\$?\b\d[\d,.]*\b|\b(one|two|three|four|five|six|seven|eight|nine|ten|twice|dozen|couple)\b", re.I),
  "t0": None,
  "date": re.compile(r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b|\b\d{1,2}/\d{1,2}\b|\b(last|this) (week|month|weekend|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b|\b(yesterday|ago)\b", re.I),
}
g, gt = gold(sys.argv[1]), gold_turns()
cnt = {"gold": collections.Counter(), "other": collections.Counter()}; n = {"gold": 0, "other": 0}
for q in questions(sys.argv[1]):
    gg = g.get(q.question_id)
    if not gg or gg["question_type"] != "multi-session" or gg["abstain"]:
        continue
    h = history(sys.argv[1], q.history_id); A = set(gt.get(q.question_id, []))
    for s in h["sessions"]:
        if s["session_id"] not in gg["evidence"]:
            continue
        for i, t in enumerate(s["turns"]):
            if t["role"] != "user":
                continue
            k = "gold" if t["turn_id"] in A else "other"
            n[k] += 1
            for c, rx in CUES.items():
                hit = (i == 0) if c == "t0" else bool(rx.search(t["content"]))
                cnt[k][c] += hit
for k in cnt:
    print(k, n[k], {c: round(v / n[k], 2) for c, v in cnt[k].items()})
