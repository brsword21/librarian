"""R4: quote precision of the hint line, from sweep per_question.jsonl (dev/dev200 have gold).
A quote is 'good' when the gold answer string occurs in it (case-folded), 'turn' when the quoted sentence occurs in a
gold turn's text, else 'BAD'. Reports v2 quotes and fallback quotes separately."""
import json, re, sys
from core.data import gold, questions
from core.gold_turns import gold_turns

split, path = sys.argv[1], sys.argv[2]
G = gold(split) if callable(gold) else gold
GT = gold_turns()
QH = {q.question_id: q.history_id for q in questions(split)}


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


rows = [json.loads(l) for l in open(path)]
from core.index import HistoryIndex
stats = {}
for r in rows:
    m = re.search(r'Likely the line you need \(assistant, session of .*?\): "(.*)"', r["hint"] or "")
    if not m:
        continue
    kind = "fallback" if (r.get("debug") or {}).get("fb") == "quote" else "v2"
    quote = m.group(1)
    g = G[r["question_id"]]
    ans = g.get("answer") if isinstance(g, dict) else getattr(g, "answer", "")
    ok_ans = norm(ans) and norm(ans) in norm(quote)
    tids = set(GT.get(r["question_id"], []))
    turn_texts = []
    for p in r["passages"]:
        pass
    verdict = "ans" if ok_ans else "?"
    if verdict == "?":
        # does the quote sit inside a gold turn?
        hid = QH.get(r["question_id"])
        if hid:
            hx = HistoryIndex.load(split, hid)
            for s in hx.sessions:
                for t in s["turns"]:
                    if t["turn_id"] in tids and norm(quote)[:80] in norm(t["content"]):
                        verdict = "turn"
        if verdict == "?":
            verdict = "BAD"
    stats.setdefault(kind, {}).setdefault(verdict, 0)
    stats[kind][verdict] += 1
    if kind == "fallback" or verdict == "BAD":
        print(f"[{kind} {verdict}] {r['question_id']} Q={r['question'][:90]!r}\n    gold={str(ans)[:80]!r}\n    quote={quote[:160]!r}")
print(stats)
