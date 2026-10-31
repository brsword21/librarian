"""Within the best session: which priority order gets the gold turn into the pack at the smallest budget?
Usage: .venv/bin/python -m lenses.ssa.scratch_a.turn_rank <split> [limit]
Scorers: lens (current recqs_cf7 order), ce_raw (cross-encoder, raw question), ce_q (CE, cleaned query),
fuse (rank-RRF of lens order and ce_raw), round (assistant turn + preceding user turn CE)."""
import sys
from collections import defaultdict

from core.data import gold, questions
from core.gold_turns import gold_turns
from core.index import HistoryIndex
from core.pack import build_pack
from lenses.ssa import a_recsent as L

split = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
g = gold(split)
gt = gold_turns()
qs = [q for q in questions(split) if g[q.question_id].get("question_type") in ("single-session-assistant", "ssa")][:limit]
P = L.VARIANTS["recqs_cf7"]
budgets = [2500, 3000, 3500, 4000, 4500, 5000, 6000, 7000]
hit = defaultdict(lambda: defaultdict(int))
chars = defaultdict(lambda: defaultdict(int))
rank1 = defaultdict(int)
n = 0
for q in qs:
    hx = HistoryIndex.load(split, q.history_id)
    A = set(gt.get(q.question_id, []))
    if not A:
        continue
    pk = L.build(q, hx, _variant="recqs_cf7", **P)
    rk = pk.debug["ranking"]
    b = rk[0]
    bu = hx.units[b]
    sid = bu.session_id
    turns = hx.sess_by_id[sid]["turns"]
    suids = [i for t in turns for i in hx.turn_units(t["turn_id"])]
    qp = L.parse_question(q.question)
    query = L.retrieval_query(qp)
    n += 1
    # lens order (as in build, single session)
    lens_order = list(hx.turn_units(bu.turn_id))
    if bu.turn_idx > 0:
        lens_order += hx.turn_units(turns[bu.turn_idx - 1]["turn_id"])[-2:]
    lens_order += [i for i in rk if hx.units[i].session_id == sid] + suids
    lens_order = list(dict.fromkeys(lens_order))
    ce_raw = dict(hx.rerank(q.question, suids))
    ce_q = dict(hx.rerank(query, suids))
    # turn scores
    tids = [t["turn_id"] for t in turns]
    def turn_order(score):
        ts = {t: max(score[i] for i in hx.turn_units(t)) for t in tids}
        return sorted(tids, key=lambda t: -ts[t])
    def expand(tord, with_prev=True):
        out = []
        for t in tord:
            out += hx.turn_units(t)
            ti = tids.index(t)
            if with_prev and ti > 0 and hx.units[hx.turn_units(t)[0]].role == "assistant":
                out += hx.turn_units(tids[ti - 1])[-1:]
        return list(dict.fromkeys(out + suids))
    pos_lens = {u: r for r, u in enumerate(lens_order)}
    lens_t = sorted(tids, key=lambda t: min(pos_lens[i] for i in hx.turn_units(t)))
    raw_t = turn_order(ce_raw)
    q_t = turn_order(ce_q)
    # fuse turn ranks
    fz = defaultdict(float)
    for lst in (lens_t, raw_t, q_t):
        for r, t in enumerate(lst):
            fz[t] += 1 / (3 + r)
    fuse_t = sorted(tids, key=lambda t: -fz[t])
    # assistant-role prior on CE: user turns penalised unless role user
    role = qp["role"]
    ce_role = {i: ce_raw[i] + ce_q[i] - (3.0 if (role != "user" and hx.units[i].role == "user") else 0.0) for i in suids}
    role_t = turn_order(ce_role)
    fz2 = defaultdict(float)
    for lst in (lens_t, role_t):
        for r, t in enumerate(lst):
            fz2[t] += 1 / (2 + r)
    fuse2_t = sorted(tids, key=lambda t: -fz2[t])
    orders = {"lens": lens_order, "lens_t": expand(lens_t), "ce_raw": expand(raw_t), "ce_q": expand(q_t),
              "fuse": expand(fuse_t), "ce_role": expand(role_t), "fuse2": expand(fuse2_t)}
    for name, t_ord in (("lens_t", lens_t), ("ce_raw", raw_t), ("ce_q", q_t), ("fuse", fuse_t), ("ce_role", role_t),
                        ("fuse2", fuse2_t)):
        rank1[name] += t_ord[0] in A
    for name, order in orders.items():
        for B in budgets:
            _, inc, c = build_pack(q, hx, order, budget=B, window=0, order="chrono", hint=pk.hint, max_sessions=1)
            ok = A <= inc
            hit[name][B] += ok
            chars[name][B] += c
print(f"{split}: n={n}")
print("turn@1:", {k: round(v / n, 3) for k, v in rank1.items()})
print("budget".ljust(10) + "".join(f"{B:>12}" for B in budgets))
for name in hit:
    print(name.ljust(10) + "".join(f"{hit[name][B]/n:7.3f}/{chars[name][B]/n/1000:3.1f}k" for B in budgets))
