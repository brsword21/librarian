"""Round 3 (SSA-A): role features for every question the text router sends to ssu or multi (dev, dev200, test).
Writes lenses/ssa/scratch_a/r3/role_feats_<split>.jsonl. Label = gold type == ssa (dev splits)."""
import json, sys, re
from concurrent.futures import ThreadPoolExecutor
from core.data import questions, gold
from core.index import HistoryIndex
from core.router import route
from harness.sweep import load_lens

brole = load_lens("lenses/ssa/b_role.py")
arec = load_lens("lenses/ssa/a_recsent.py")

def feats(split, q):
    hx = HistoryIndex.load(split, q.history_id)
    fb = brole.role_features(q, hx)
    fa = arec.role_features(q, hx)
    p_b = brole.role_guess(q, hx)
    out = {"qid": q.question_id, "q": q.question, "route": route(q.question)[0], "p_b": p_b,
           "d": fb["d"], "ce_a": fb["ce_a"], "ce_u": fb["ce_u"], "n_first": fb["n_first"],
           "top_role": hx.units[fb["top_uid"]].role if fb["top_uid"] is not None else None}
    out.update({f"a_{k}": v for k, v in fa.items()})
    return out

split = sys.argv[1]
G = gold(split) if split != "test" else {}
qs = [q for q in questions(split) if route(q.question)[0] in ("ssu", "multi")]
with ThreadPoolExecutor(1 if split == "test" else 2) as ex:
    rows = list(ex.map(lambda q: feats(split, q), qs))
with open(f"lenses/ssa/scratch_a/r3/role_feats_{split}.jsonl", "w") as f:
    for r in rows:
        g = G.get(r["qid"], {})
        r["gold"] = g.get("question_type"); r["abstain"] = g.get("abstain")
        f.write(json.dumps(r) + "\n")
print(split, len(rows))
