"""For each answerable question where ATR<1: per missing gold turn, its best unit's position in `ranked`, its position
within its session (by final score), whether its session is in the pack and how many units that session got.
    .venv/bin/python -m lenses.multi.scratch_b.atr_diag <variant> [split] [limit]"""
import sys
from core.data import questions, gold
from core.gold_turns import gold_turns
from core.index import HistoryIndex
from core.types import SHORT
from lenses.multi import b_sweep as L

v = sys.argv[1]; split = sys.argv[2] if len(sys.argv) > 2 else "dev"; lim = int(sys.argv[3]) if len(sys.argv) > 3 else 40
G, GT = gold(split), gold_turns()
qs = [q for q in questions(split) if q.question_id in G and SHORT[G[q.question_id]["question_type"]] == "multi"
      and not G[q.question_id]["abstain"]][:lim]
for q in qs:
    hx = HistoryIndex.load(split, q.history_id)
    p = L.build(q, hx, _variant=v, **L.VARIANTS[v])
    A = set(GT.get(q.question_id, []))
    miss = A - p.included_turns
    if not miss:
        continue
    ranked = p.debug["ranking"]
    pos = {u: i for i, u in enumerate(ranked)}
    print(f"{q.question_id} {q.question[:80]}  ATR={len(A & p.included_turns)}/{len(A)}")
    for t in miss:
        us = hx.turn_units(t)
        sid = hx.units[us[0]].session_id
        best = min((pos.get(u, 9999), u) for u in us)
        sess_units = [u for u in ranked if hx.units[u].session_id == sid]
        within = sess_units.index(best[1]) if best[1] in sess_units else None
        inpack = sid in {x.id for x in p.passages}
        print(f"   turn {t} role={hx.units[us[0]].role} tidx={hx.units[us[0]].turn_idx} rank={best[0]} within_sess={within} "
              f"sess_in_pack={inpack} :: {hx.units[best[1]].text[:150]!r}")
