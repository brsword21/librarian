"""Dump test packs (question/hint + passages) for given qids from a packs jsonl."""
import json, sys
path = sys.argv[1]
qids = set(sys.argv[2:])
for l in open(path):
    r = json.loads(l)
    if qids and r["question_id"] not in qids:
        continue
    print("=" * 100)
    print(r["question_id"], r.get("route"), r.get("lens"), r.get("variant"), "chars", r.get("chars"), "cite", r.get("cite_plan"), "abst", r.get("abstain_p"), "comp", r.get("computed"))
    print("Q:", r["question"])
    for i, p in enumerate(r["passages"], 1):
        print(f"--- [E{i}] {p.get('id')} {p.get('date')}")
        print(p.get("text", "")[:int(sys.argv[0] and 2500)])
