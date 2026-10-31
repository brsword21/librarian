"""R2: where is the newest gold session relative to the cite pair? (pair-only packing feasibility)"""
import json, sys
from core.data import gold
split = sys.argv[2] if len(sys.argv) > 2 else "dev"
g = gold(split)
rows = [json.loads(l) for l in open(sys.argv[1])]
from core.index import HistoryIndex
n = 0
for r in rows:
    if r["abstain_gold"]:
        continue
    ev = g[r["question_id"]]["evidence"]
    cp = r["cite_plan"] or []
    pk = [p["id"] for p in r["passages"]]
    hit = set(cp) & set(ev)
    if len(hit) < 2 or r["PA"] < 1:
        n += 1
        print(f'{r["question_id"]} PA={r["PA"]} CF1={r["CF1"]:.2f} ATR={r["ATR"]:.2f} gold={ev} cite={cp} pack={pk} | {r["question"][:80]}')
print("bad", n)
