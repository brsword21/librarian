"""CF1 / PA misses of a sweep run (harness.failures lists only PA<1): planned pair vs gold sessions.
usage: .venv/bin/python lenses/ku/scratch_b/cf1_miss.py runs/<tag>/ku/<lens>/<variant>/<split> [--n 20]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from core.data import gold, history, questions  # noqa: E402
from core.gold_turns import gold_turns  # noqa: E402

run = Path(sys.argv[1])
n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 20
split = run.name
rows = [json.loads(l) for l in open(run / "per_question.jsonl")]
g, gt = gold(split), gold_turns()
qmap = {q.question_id: q for q in questions(split)}
bad = [r for r in rows if not r.get("abstain_gold") and not r.get("error") and (r.get("CF1", 1) < 1 or r.get("PA", 1) < 1)]
ab = [r for r in rows if r.get("abstain_gold")]
print(f"{len(rows)} rows, {len(bad)} answerable with CF1<1 or PA<1; unanswerable abstain_p:",
      [round(r["abstain_p"], 2) for r in ab])
hi = sorted([r for r in rows if not r.get("abstain_gold")], key=lambda r: -r["abstain_p"])[:5]
print("highest abstain_p on answerable:", [(r["question"][:50], round(r["abstain_p"], 2)) for r in hi])
for r in bad[:n]:
    q, gg = qmap[r["question_id"]], g[r["question_id"]]
    h = history(split, q.history_id)
    sess = {s["session_id"]: (i, s) for i, s in enumerate(h["sessions"])}
    G = gg["evidence"]
    print("=" * 100)
    print(f"{r['question_id']} {q.question} | GOLD {gg['answer'][:80]}")
    print(f"  PA={r['PA']} CF1={r['CF1']:.2f} ATR={r['ATR']:.2f} chars={r['chars']} plan={r.get('cite_plan')} "
          f"mode={r.get('debug', {}).get('mode')}")
    for sid in G:
        i, s = sess[sid]
        tids = [t for t in gt.get(r["question_id"], []) if any(tt["turn_id"] == t for tt in s["turns"])]
        txt = " ".join(tt["content"] for tt in s["turns"] if tt["turn_id"] in tids)
        print(f"  GOLD [{i:3d}] {sid} {'IN' if sid in (r.get('cite_plan') or []) else 'out'}: {txt[:260]!r}")
    for sid in (r.get("cite_plan") or []):
        if sid not in G:
            i, s = sess[sid]
            print(f"  WRONG[{i:3d}] {sid}")
    if r.get("hint"):
        print("  HINT:", r["hint"][:600].replace("\n", " | "))
