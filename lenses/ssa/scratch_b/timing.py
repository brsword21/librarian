import time, sys
from core.data import gold, questions
from core.index import HistoryIndex
from core.types import SHORT
split = sys.argv[1]; off = int(sys.argv[2]) if len(sys.argv) > 2 else 4
g = gold(split)
qs = [q for q in questions(split) if q.question_id in g and SHORT[g[q.question_id]["question_type"]] == "ssa"]
print(len(qs), "ssa questions;", len({q.history_id for q in qs}), "histories")
for q in qs[off:off+2]:
    t0 = time.time(); hx = HistoryIndex.load(split, q.history_id); t1 = time.time()
    b = hx.bm25(q.question, k=100); t2 = time.time()
    d = hx.dense(q.question, k=100); t3 = time.time()
    r = hx.rerank(q.question + " x", [u for u, _ in b[:40]]); t4 = time.time()
    print(q.history_id, len(hx.units), f"load {t1-t0:.1f}s bm25 {t2-t1:.1f}s dense {t3-t2:.1f}s rerank40 {t4-t3:.1f}s")
