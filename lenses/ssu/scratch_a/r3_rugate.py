"""Round 3: typed value disagreement between a_struct2's primary and outlier runner-up (best units)."""
import json, sys
from collections import Counter
from core.data import gold, questions
from core.index import HistoryIndex
from harness.sweep import load_lens
from lenses.ssu.a_owner import parse_question, unit_class
R = load_lens("lenses/ssu/a_r3_route.py")
S2 = load_lens("lenses/ssu/a_struct2.py")
for split, path in [("dev", "runs/r3-ssu-a/ssu-routed/a_r3_route/v1/dev/per_question.jsonl"),
                    ("dev200", "runs/r3-ssu-a/ssu-routed/a_r3_route/v1/dev200/per_question.jsonl"),
                    ("test", "runs/audit/all/pipeline/routed/test_packs.jsonl")]:
    g = gold(split) if split != "test" else {}
    qs = {q.question_id: q for q in questions(split)}
    c = Counter()
    for l in open(path):
        r = json.loads(l)
        if r.get("route") != "ssu":
            continue
        d = r.get("debug") or {}
        if not d.get("runner"):
            continue
        q = qs[r["question_id"]]
        hx = HistoryIndex.load(split, q.history_id)
        pk = S2.build(q, hx, _variant="r3rn", **S2.VARIANTS["r3rn"])
        d = pk.debug
        qp = parse_question(q.question)
        prim = (pk.cite_plan or [None])[0]
        best = {}
        for uid in d.get("ranking", []):
            s = hx.units[uid].session_id
            if s not in best:
                best[s] = uid
        if prim not in best or d["runner"] not in best:
            continue
        scs = [unit_class(hx.units[best[s]], qp) for s in (prim, d["runner"])]
        own = all(sc.owner != "mismatch" and sc.polarity not in ("neg", "plan") for sc in scs)
        tv = [R.typed_values(sc.sent, q.question) for sc in scs]
        dis = R.disagree(*tv)
        t = g[q.question_id]["question_type"][:5] if q.question_id in g else "?"
        ev = set(g[q.question_id]["evidence"]) if q.question_id in g else set()
        fire = bool(own and dis)
        c[(t, fire, d["runner"] in ev)] += 1
        if fire:
            print(split, t, q.question_id, dis, "runner_gold" if d["runner"] in ev else "", "|", q.question[:70], "||", scs[0].sent[:80], "||", scs[1].sent[:80])
    print(split, dict(c))
