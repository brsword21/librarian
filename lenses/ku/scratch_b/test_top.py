"""Qualitative: top BM25 user units for test KU-style questions (no gold; audit only, no tuning on single items)."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from core.index import HistoryIndex
K = int(sys.argv[1]) if len(sys.argv) > 1 else 8
rows = [json.loads(l) for l in open(ROOT / "runs/samples/ku.jsonl")]
for r in rows:
    if r["split"] != "test":
        continue
    hx = HistoryIndex.load("test", r["history_id"])
    q = r["question"]
    print("=" * 10, q)
    for uid, s in hx.bm25(q, k=K, roles="user"):
        u = hx.units[uid]
        # print the best-matching sentence only
        sents = re.split(r"(?<=[.!?])\s+", u.text)
        qt = set(re.findall(r"[a-z]{4,}", q.lower()))
        best = max(sents, key=lambda x: len(qt & set(re.findall(r"[a-z]{4,}", x.lower()))))
        print(f"  {s:5.1f} [{u.sess_idx:3d}] {u.date_str[:10]} t{u.turn_idx} {best[:200]}")
