"""SSU lens B "Semantyka", round 1: retrieval-centric single-session-user lens.

The answer is one USER turn, usually a side remark, and the assistant usually echoes it ("Golden Retrievers like Max
deserve ..."). So the lens:
  1. pools units with hybrid (BM25 + bge, RRF) over ALL roles (the assistant echo is strong session evidence), plus
     optionally a user-only hybrid channel,
  2. reranks the pool with the cross-encoder (query = the exact question string, so caches are shared),
  3. scores sessions by MAX-pooling (best unit; a side remark must not be diluted by the session topic), with a small
     handicap for assistant units,
  4. sweeps the top `sweep` sessions: every USER unit there is reranked (finds the short reply / the side remark that the
     pool missed while its assistant echo ranked high),
  5. cites the top session (+ the runner-up when the margin is small: F1 pays for a 2nd cite when p2 > p1/2),
  6. packs the best USER unit(s) of the top `n_sess` sessions (+ the assistant chunk before each, which carries the
     question a short reply answers) under a small budget,
  7. abstain_p from the calibrated top logit and whether the rarest question term appears near the top.
Options: light decoy tags from b_mentions (other person / negated / tentative), recency ("end up", "now", "the last X
I mentioned") as a time-decay towards the latest near-top session, a short own-statement hint.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict

from core.types import EvidencePack

HINT = ("Answer from the user's own statements about themself; mentions of other people's things, plans, or things "
        "the user did not do are not the answer.")

_BASE = dict(pool=300, k_all=100, k_user=0, rrf_k=60, w_bm25=1.0, w_dense=1.0, asst_pen=0.0, lam_second=0.0,
             sweep=3, n_sess=6, drop=10.0, budget=6000, before=1, after=0, cited_units=3, cited_after=1,
             other_units=1, unit_cut=6.0, reply_len=200, cite_margin=0.0, tags=False, pen_other=2.0, pen_neg=2.0, pen_tent=1.5,
             recency=False, rec_delta=2.0, hint="", ab_bias=0.0, ab_temp=2.0, ab_cov=0.3, ab_mode="df",
             ab_absent=0.6)

VARIANTS = {
    "sem": dict(_BASE),
    "sem_nosweep": {**_BASE, "sweep": 0},
    "sem_cu5": {**_BASE, "cited_units": 5, "unit_cut": 99.0},
    "sem_cu5r": {**_BASE, "cited_units": 5, "unit_cut": 99.0, "before": "reply"},
    "sem_cu5r0": {**_BASE, "cited_units": 5, "unit_cut": 99.0, "before": "reply", "cited_after": 0},
    "sem_tags": {**_BASE, "cited_units": 5, "unit_cut": 99.0, "before": "reply", "tags": True},
    "sem_abp": {**_BASE, "cited_units": 5, "unit_cut": 99.0, "before": "reply", "tags": True, "ab_mode": "prefix"},
    "sem_abp2": {**_BASE, "cited_units": 5, "unit_cut": 99.0, "before": "reply", "tags": True, "ab_mode": "prefix",
                 "ab_temp": 3.0, "ab_bias": -1.0},
    "best": {**_BASE, "cited_units": 5, "unit_cut": 99.0, "before": "reply", "tags": True, "ab_mode": "prefix",
             "hint": "own"},
    "best_rec": {**_BASE, "cited_units": 5, "unit_cut": 99.0, "before": "reply", "tags": True, "ab_mode": "prefix",
                 "hint": "own", "recency": True},
    "sem_m1": {**_BASE, "cited_units": 5, "unit_cut": 99.0, "before": "reply", "cite_margin": 1.0},
    "sem_asst1": {**_BASE, "cited_units": 5, "unit_cut": 99.0, "before": "reply", "asst_pen": 1.0},
}

STOP = set("""a an the of to in on at for with my me i we our you your is are was were be been do did does what which who
whom where when how many much that this those these it its by from about as or and before after have has had any some
i've i'm i'd me myself us up out over into than then there their they them can could would should will just so name
names named call called kind type sort favorite favourite usually currently current now last first mention mentioned
tell told end ended get got new still really actually exactly long""".split())


def _words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9'-]*", s.lower())


def _stem(w: str) -> str:
    w = re.sub(r"'s$", "", w.lower())
    for suf in ("ings", "ing", "ies", "ied", "es", "ed", "s"):
        if len(w) - len(suf) >= 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _sig(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))


_DF: dict = {}


def _df(hx) -> dict:
    key = (hx.split, hx.history_id)
    if key not in _DF:
        df: dict = defaultdict(int)
        for u in hx.units:
            if u.role == "user":
                for w in set(_stem(w) for w in _words(u.index_text)):
                    df[w] += 1
        _DF.clear()
        _DF[key] = df
    return _DF[key]


_RECENCY = re.compile(r"\bend(?:ed)? up\b|\b(?:the )?(?:last|latest|most recent)\b[\w\s'-]{0,40}\bI\b[\w\s'-]{0,20}"
                      r"\b(?:mention|told|said|talk)|\b(?:now|currently|current|these days|right now|finally|settle[ds]? on)\b",
                      re.I)


def build(q, hx, **params) -> EvidencePack:
    from core.pack import build_pack

    p = {**_BASE, **params}
    question = q.question
    U = hx.units

    # 1. pool: all-role hybrid (+ optional user-only channel)
    cand: list[int] = [u for u, _ in hx.hybrid(question, k=p["k_all"], pool=p["pool"], rrf_k=p["rrf_k"],
                                                w_bm25=p["w_bm25"], w_dense=p["w_dense"])]
    if p["k_user"]:
        cand += [u for u, _ in hx.hybrid(question, k=p["k_user"], roles=["user"], pool=p["pool"], rrf_k=p["rrf_k"],
                                          w_bm25=p["w_bm25"], w_dense=p["w_dense"])]
    cand = list(dict.fromkeys(cand))
    # 2. rerank
    rr = dict(hx.rerank(question, cand)) if cand else {}

    def sess_scores(scores: dict) -> list:
        by: dict[str, list[float]] = defaultdict(list)
        for u, s in scores.items():
            by[U[u].session_id].append(s - (p["asst_pen"] if U[u].role == "assistant" else 0.0))
        out = []
        for sid, v in by.items():
            v.sort(reverse=True)
            out.append((v[0] + (p["lam_second"] * max(0.0, v[1]) if len(v) > 1 else 0.0), sid))
        return sorted(out, reverse=True)

    # 4. session sweep: rerank every user unit of the top sessions
    if p["sweep"] and rr:
        top_sids = [sid for _, sid in sess_scores(rr)[: p["sweep"]]]
        more = [u.uid for u in U if u.session_id in top_sids and u.role == "user" and u.uid not in rr]
        if more:
            rr.update(dict(hx.rerank(question, more)))
    sc = dict(rr)
    tags_of: dict[int, set] = {}
    if p["tags"] and sc:
        from lenses.ssu.b_mentions import parse_question, tag_mention
        pq = parse_question(question)
        for u in sc:
            if U[u].role != "user":
                continue
            t = tag_mention(U[u].text, U[u].ctx, pq)
            tags_of[u] = t
            if "other" in t and "reply_named" not in t:
                sc[u] -= p["pen_other"]
            if "negated" in t:
                sc[u] -= p["pen_neg"]
            if "tentative" in t and "update" not in t:
                sc[u] -= p["pen_tent"]
    ranked = sorted(sc, key=lambda u: -sc[u])
    sess = sess_scores(sc)
    top = sess[0][0] if sess else -20.0
    chosen = [sid for s, sid in sess if s >= top - p["drop"]][: p["n_sess"]] or [sid for _, sid in sess[:1]]
    s_of = dict((sid, s) for s, sid in sess)

    # 5. cite plan (+ optional recency: the latest near-top session)
    recency = bool(p["recency"] and _RECENCY.search(question))
    cite = chosen[:1]
    if recency and chosen:
        near = [sid for sid in chosen if s_of[sid] >= top - p["rec_delta"]]
        cite = [max(near, key=lambda sid: hx.sess_by_id[sid]["sess_idx"])]
    elif p["cite_margin"] and len(chosen) > 1 and s_of[chosen[0]] - s_of[chosen[1]] < p["cite_margin"]:
        cite.append(chosen[1])

    # 6. pack: best USER unit(s) per chosen session (+ the assistant chunk before, + the next chunk when cited)
    order: list[int] = []
    for sid in chosen:
        us = [u for u in ranked if U[u].session_id == sid]
        uu = [u for u in us if U[u].role == "user"] or us[:1]
        k = p["cited_units"] if sid in cite else p["other_units"]
        for i, u in enumerate(uu[:k]):
            if i and sc[u] < sc[uu[0]] - p["unit_cut"]:
                break
            if p["before"] == "reply":   # the assistant chunk before a short reply carries what it answers
                short = U[u].chunk_idx == 0 and len(U[u].text) < p["reply_len"] and U[u].ctx.rstrip().endswith("?")
                order += hx.neighbors(u, 1 if short else 0, 0)
            else:
                order += hx.neighbors(u, p["before"], 0)
            if sid in cite and p["cited_after"] and i == 0:
                order += hx.neighbors(u, 0, p["cited_after"])
    order = list(dict.fromkeys(order))

    # 7. abstention: calibrated top logit x coverage of the rarest question term in the top units
    best = max(rr.values()) if rr else -20.0
    p_ans = _sig((best - p["ab_bias"]) / p["ab_temp"])
    pen = 0.0
    if p["ab_mode"] == "prefix":
        # prefix document frequency over USER units (robust to inflection: graduate ~ graduated, bake ~ baked)
        terms = {_stem(w) for w in _words(question.split("?")[0]) if w not in STOP and len(w) > 2}
        rx = {t: re.compile(r"\b" + re.escape(t[: max(4, len(t) - 1)])) for t in terms}
        utexts = [u.text.lower() for u in U if u.role == "user"]
        dfp = {t: sum(1 for x in utexts if rx[t].search(x)) for t in terms}
        if terms:
            rare = min(terms, key=lambda t: (dfp[t], t))
            top_user = [u for u in ranked if U[u].role == "user"][:3]
            top_text = " ".join(U[u].text.lower() for u in top_user)
            if dfp[rare] == 0:
                pen = p["ab_absent"]
            elif not rx[rare].search(top_text):
                pen = p["ab_cov"]
    else:
        df = _df(hx)
        terms = sorted({_stem(w) for w in _words(question.split("?")[0]) if w not in STOP and len(w) > 2},
                       key=lambda t: df.get(t, 0))
        if terms:
            rare = terms[0]
            top_text = " ".join(U[u].index_text.lower() for u in ranked[:3])
            if df.get(rare, 0) == 0 or not re.search(r"\b" + re.escape(rare[: max(4, len(rare))]), top_text):
                pen = p["ab_cov"]
    abstain_p = max(0.0, min(1.0, 1.0 - p_ans * (1.0 - pen)))

    hint = HINT if p["hint"] == "own" else ""
    if recency and hint:
        hint += " If the user gave different values at different times, the most recent dated statement wins."
    passages, included, _chars = build_pack(q, hx, order, budget=p["budget"], window=0, order="chrono", hint=hint,
                                            max_sessions=p["n_sess"])
    in_pack = {ps.id for ps in passages}
    cite = [c for c in cite if c in in_pack] or [ps.id for ps in passages[:1]]
    return EvidencePack(question_id=q.question_id, variant=params.get("_variant", ""), route="ssu",
                        passages=passages, hint=hint, cite_plan=cite, abstain_p=abstain_p,
                        included_turns=included, computed=None,
                        debug={"ranking": ranked, "best": best, "sessions": [(round(s, 2), sid) for s, sid in sess[:8]]})
