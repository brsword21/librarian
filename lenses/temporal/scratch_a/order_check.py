"""Dev 'which happened first, A or B' questions: does the calendar's earlier event match the gold answer?"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from core.data import gold, questions, history  # noqa
from lenses.temporal.a_calendar import analyse, _FakeHX, toks  # noqa

g = gold("dev")
ok = n = 0
for q in questions("dev"):
    gg = g[q.question_id]
    if gg["question_type"] != "temporal-reasoning" or gg["abstain"]:
        continue
    qp, picks, alts, computed, conf = analyse(q, _FakeHX(history("dev", q.history_id)))
    if qp.kind != "order" or len(picks) != 2 or not all(m for _, m, _ in picks):
        continue
    first = min(picks, key=lambda x: x[1].value)[0]
    other = max(picks, key=lambda x: x[1].value)[0]
    ans = {t for t, _ in toks(str(gg["answer"]))}
    s1 = len(ans & {t for t, _ in toks(first)}) / max(1, len({t for t, _ in toks(first)}))
    s2 = len(ans & {t for t, _ in toks(other)}) / max(1, len({t for t, _ in toks(other)}))
    n += 1
    hit = s1 > s2
    ok += hit
    tie = picks[0][1].value == picks[1][1].value
    print(("OK " if hit else "XX ") + ("TIE " if tie else "") + q.question[:90], "=>", str(gg["answer"])[:50])
print(ok, n)
