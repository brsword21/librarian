import json, sys
from core.data import questions, gold
split = sys.argv[1] if len(sys.argv) > 1 else "dev"
g = gold(split)
qs = [q for q in questions(split) if g.get(q.question_id, {}).get("question_type") == "multi-session"]
print(len(qs))
for q in qs:
    gg = g[q.question_id]
    print(f"{q.question_id} {q.date_str[:10]} ab={int(gg['abstain'])} ev={len(gg['evidence'])} | {q.question} | {str(gg['answer'])[:90]}")
