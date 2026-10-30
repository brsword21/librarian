"""For PA failures: which gold turns are missing, is their session in the pack, and where they rank."""
import sys, json
from core.data import questions, gold
from core.gold_turns import gold_turns
from core.index import HistoryIndex
from lenses.multi import a_tally as L
split, var = sys.argv[1], sys.argv[2]
g, gt = gold(split), gold_turns()
qs = {q.question_id: q for q in questions(split)}
rows = json.load(open(f"lenses/multi/scratch_a/eval_{split}_{var}.json"))
for r in rows:
    if r["PA"]:
        continue
    q = qs[r["qid"]]; gg = g[q.question_id]
    hx = HistoryIndex.load(split, q.history_id)
    pk = L.build(q, hx, _variant=var, **L.VARIANTS[var])
    rank = {uid: i for i, uid in enumerate(pk.debug["ranking"])}
    P = set(pk.session_ids())
    print(f"\n### {q.question} ALL={r['ALL']} ATR={r['ATR']:.2f} q='{pk.debug['query']}'")
    for tid in gt.get(q.question_id, []):
        if tid in pk.included_turns:
            continue
        us = hx.turn_units(tid)
        u = hx.units[us[0]]
        best = min((rank.get(x, 9999) for x in us))
        print(f"   miss sess_in_pack={u.session_id in P} unit_rank={best} n_units={len(us)} | {u.text[:200]!r}")
