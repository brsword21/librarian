"""Qualitative look at a test pack (no gold): python show_test.py '<question substring>' [variant] [k=v ...]"""
import sys
from core.data import questions
from core.index import HistoryIndex
from lenses.multi import a_tally as L
sub, var = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "bm25")
extra = {k: (int(v) if v.isdigit() else v) for k, v in (a.split("=") for a in sys.argv[3:])}
for q in questions("test"):
    if sub.lower() not in q.question.lower():
        continue
    hx = HistoryIndex.load("test", q.history_id)
    pk = L.build(q, hx, _variant=var, **{**L.VARIANTS[var], **extra})
    print(q.question, q.date_str, "| window:", pk.debug["window"], "used:", pk.debug["window_used"], "| kind", pk.debug["kind"])
    print("HINT:", pk.hint)
    print("cite:", pk.cite_plan, "abstain_p", pk.abstain_p, pk.debug["abstain_why"], "chars", L.message_chars(q.question, pk.hint, pk.passages))
    for i, p in enumerate(pk.passages, 1):
        print(f"[E{i}] {p.date[:10]} {p.id} {p.text[:400]!r}")
    break
