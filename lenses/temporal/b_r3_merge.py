"""Temporal lens B, round 3: the frozen v1 temporal route (lenses/temporal/merged_r2.py evA_mixB = A's a_gap ct_evgba
for gap / named-event questions, b_merge ev1_mix_g for the rest) with B-side changes, each switchable per variant.
`base` reproduces merged_r2 evA_mixB exactly. Frozen files are imported, never edited.

1. `agree`    gap fallback by agreement: A withheld its computed gap on its plain confidence gate (gate None; never on
              rounding / sign / zero / who / absent, where B does the same arithmetic) but its raw value equals the
              value B's event route computes independently (+/-1 day) -> emit it, with B's dated picks in the hint
              (brief r3 1). On test it fires 0 times: Montreal = 45 is already emitted by A in v1.
   `fbg`      looser: b_merge's guarded fallback (B's computed whenever A has none and the guard passes).
2. `oq_head`  whole-question route (no parsed events): the user units of the cited sessions (and, with `head_k`, of
              the next sessions of the time-prior ranking up to head_k) are CE-scored one by one (+ `w_today` for
              "today / yesterday / just" when the question has a relative anchor), and their best `head_per` units
              enter the pack first, interleaved across sessions. r2 packed units by global rank, so a session often
              entered through a sibling unit and the gold turn ("I just planted 12 new tomato saplings today") stayed
              out.
   `oq_cap`   whole-question route packs at most len(cite) + `oq_extra` sessions (brief r3 2). Rejected: ALL drops.
   `div`      one unit per session before any second unit (more category-mates). Rejected: ATR drops.
   `strip`    plain-CE ranking on the question without its time phrase. Rejected: no gain.
3. `ord_fill` order / "first" questions on A's route. `ord_first`: the opening user unit of every packed session is
              pinned (dev gold turns are mostly the opening turn). `ord_sent`: sentence-level hx.rerank_texts of the
              event phrase vs the packed sessions' user units, pinned above `ord_thr` (brief r3 3; no gain on dev).
Best: `r3_hk6` (agree + oq_head head_per 3 head_k 6 + ord_first). Report: lenses/temporal/b_report.md.
"""
from __future__ import annotations

import math
import re
from datetime import timedelta

from core.types import EvidencePack
from harness.sweep import load_lens

_M = load_lens("lenses/temporal/merged_r2.py")
_A = _M._A                    # a_gap
_BM = _M._B                   # b_merge
_BS = _BM._B                  # b_sem
from lenses.temporal import b_evcal as E  # noqa: E402

_TODAY = re.compile(r"\b(today|yesterday|this morning|this afternoon|tonight|last night|just|earlier this week)\b", re.I)

_BASE = {"a_variant": "ct_evgba", "b_variant": "ev1_mix_g"}
VARIANTS = {
    "base": {**_BASE},
    "agree": {**_BASE, "agree": True},
    "fbg": {**_BASE, "fbg": True},
    "head2": {**_BASE, "agree": True, "oq_head": True, "head_per": 2, "w_today": 1.5},
    "head3": {**_BASE, "agree": True, "oq_head": True, "head_per": 3, "w_today": 1.5},
    "head2_c2": {**_BASE, "agree": True, "oq_head": True, "head_per": 2, "w_today": 1.5, "oq_cap": True,
                 "oq_extra": 2},
    "ord": {**_BASE, "agree": True, "ord_fill": True, "ord_thr": -3.0, "ord_per": 2},
    "ordf": {**_BASE, "agree": True, "ord_fill": True, "ord_thr": 99.0, "ord_first": True},
    "ords": {**_BASE, "agree": True, "ord_fill": True, "ord_thr": -1.0, "ord_per": 2, "ord_sent": True},
    "ordfs": {**_BASE, "agree": True, "ord_fill": True, "ord_thr": -1.0, "ord_per": 2, "ord_sent": True,
              "ord_first": True},
    # combined: agreement fallback + per-session heads on the whole-question route + opening-turn fill on order
    "r3": {**_BASE, "agree": True, "oq_head": True, "head_per": 3, "w_today": 1.5, "ord_fill": True, "ord_thr": 99.0,
           "ord_first": True},
    "r3_b8": {**_BASE, "agree": True, "oq_head": True, "head_per": 3, "w_today": 1.5, "ord_fill": True, "ord_thr": 99.0,
              "ord_first": True, "budget_other": 8000},
    "r3_b7": {**_BASE, "agree": True, "oq_head": True, "head_per": 3, "w_today": 1.5, "ord_fill": True, "ord_thr": 99.0,
              "ord_first": True, "budget_other": 7000},
    "r3_div": {**_BASE, "agree": True, "oq_head": True, "head_per": 3, "w_today": 1.5, "ord_fill": True,
               "ord_thr": 99.0, "ord_first": True, "div": True},
    "r3_div2": {**_BASE, "agree": True, "oq_head": True, "head_per": 2, "w_today": 1.5, "ord_fill": True,
                "ord_thr": 99.0, "ord_first": True, "div": True},
    "r3_hk6": {**_BASE, "agree": True, "oq_head": True, "head_per": 3, "head_k": 6, "w_today": 1.5, "ord_fill": True,
               "ord_thr": 99.0, "ord_first": True},
    "r3_hk8": {**_BASE, "agree": True, "oq_head": True, "head_per": 3, "head_k": 8, "w_today": 1.5, "ord_fill": True,
               "ord_thr": 99.0, "ord_first": True},
    "r3_hk8p2": {**_BASE, "agree": True, "oq_head": True, "head_per": 2, "head_k": 8, "w_today": 1.5, "ord_fill": True,
                 "ord_thr": 99.0, "ord_first": True},
    "r3_hk6d": {**_BASE, "agree": True, "oq_head": True, "head_per": 3, "head_k": 6, "w_today": 1.5, "ord_fill": True,
                "ord_thr": 99.0, "ord_first": True, "div": True, "div_n": 10},
    "r3_hk6_b12": {**_BASE, "agree": True, "oq_head": True, "head_per": 3, "head_k": 6, "w_today": 1.5,
                   "ord_fill": True, "ord_thr": 99.0, "ord_first": True, "budget_other": 12000},
    "h3s": {**_BASE, "agree": True, "oq_head": True, "head_per": 3, "w_today": 1.5, "strip": True},
}


# ---------------------------------------------------------------------------------------------------------------------
# 1. gap fallback by agreement
# ---------------------------------------------------------------------------------------------------------------------
def gap_agree(q, hx, pack, p: dict):
    dbg = pack.debug or {}
    raw = dbg.get("computed_raw")
    gate = dbg.get("gate") or ""
    if pack.computed is not None or raw is None:
        return pack, None
    if gate:        # rounding / sign / zero / who / absent: B computes the same arithmetic, agreement is no evidence
        return pack, None
    bp = {"b_variant": "sem_turns9", "fb_guard": True, "fb_budget": p.get("fb_budget", 9000)}
    bpk = _BS.build(q, hx, _variant="sem_turns9", **_BS.VARIANTS["sem_turns9"])
    if bpk.computed is None:
        return pack, None
    try:
        bval = int(bpk.computed)
    except ValueError:
        return pack, None
    if abs(int(raw) - bval) > 1:
        return pack, None
    picks = (bpk.debug or {}).get("picks") or []
    if not _BM._fallback_sane(bpk, picks):
        return pack, None
    pack, comp = _BM.gap_fallback(q, hx, pack, bp)
    if comp is not None:
        pack.computed = str(raw) if str(raw) == str(comp) else pack.computed
    return pack, comp


def gap_fbg(q, hx, pack, p: dict):
    if pack.computed is not None:
        return pack, None
    gate = (pack.debug or {}).get("gate") or ""
    if gate.startswith("absent"):
        return pack, None
    bp = {"b_variant": "sem_turns9", "fb_guard": True, "fb_budget": p.get("fb_budget", 9000)}
    return _BM.gap_fallback(q, hx, pack, bp)


# ---------------------------------------------------------------------------------------------------------------------
# 2. whole-question route with per-session heads
_ANCH = re.compile(r"\b(?:(?:a|one|two|three|four|five|six|seven|eight|nine|ten|\d+|a couple of|a few)\s+"
                   r"(?:days?|weeks?|months?|years?)\s+ago"
                   r"|(?:last|past|this)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week(?:end)?|month)"
                   r"|on the (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:\s+(?:a|one|two|three)\s+"
                   r"(?:weeks?|months?)\s+ago)?|I mentioned|I told you about)\b", re.I)


def strip_query(text: str) -> str:
    """'What was the social media activity I participated 5 days ago?' -> 'What was the social media activity I
    participated?' The time phrase only matches the 'today' sentences of the anchor session; the category-mates at
    other dates (also gold) are found by the topic alone."""
    t = _ANCH.sub(" ", text)
    return re.sub(r"\s+", " ", t).strip()


def strip_rank(q, hx, p: dict) -> list[int]:
    qs = strip_query(q.question)
    if qs == q.question:
        return []
    cutoff = q.date + timedelta(days=1)
    pool = [i for i, _ in hx.hybrid(qs, k=p.get("strip_k", 60), roles="user") if hx.units[i].date <= cutoff]
    if not pool:
        return []
    return [u for u, _ in sorted(hx.rerank(qs, pool), key=lambda x: -x[1])]

# ---------------------------------------------------------------------------------------------------------------------
def build_other3(q, hx, p: dict) -> EvidencePack:
    from core.pack import build_pack

    sp = {**_BS.VARIANTS["sem_turns9"]}
    rows = _BS.rank_question(hx, q, sp)
    order_uids = [r["uid"] for r in rows]
    plain = [r["uid"] for r in sorted(rows, key=lambda r: -r["ce"])]
    if p.get("strip"):
        plain = strip_rank(q, hx, p) or plain
    mix = list(dict.fromkeys(x for pair in zip(order_uids, plain) for x in pair))
    n = _BS.expected_items(q.question)
    cite = _BS.cite_sessions(rows, p.get("cite_gap8", 8.0), n if n else p.get("cite_top", 4))
    anchor = E.question_anchor(q.question, q.date)
    head = []
    hsess = list(cite)
    if p.get("head_k"):           # heads also for the next sessions of the time-prior ranking (not cited)
        for r in rows:
            if len(hsess) >= p["head_k"]:
                break
            if r["session_id"] not in hsess:
                hsess.append(r["session_id"])
    if p.get("oq_head") and cite:
        cutoff = q.date + timedelta(days=1)
        per = {}
        for sid in hsess:
            us = [u.uid for u in hx.units if u.session_id == sid and u.role == "user" and u.date <= cutoff]
            if not us:
                continue
            sc = []
            for uid, ce in hx.rerank(q.question, us):
                f = ce
                if anchor is not None and p.get("w_today") and _TODAY.search(hx.units[uid].text):
                    f += p["w_today"]
                sc.append((f, uid))
            sc.sort(reverse=True)
            per[sid] = [u for _, u in sc[: p.get("head_per", 2)]]
        for j in range(p.get("head_per", 2)):
            for sid in hsess:
                if j < len(per.get(sid, [])):
                    head.append(per[sid][j])
    if p.get("div"):              # diversity: the best unit of every session before any session's second unit
        seen, firsts = set(head and [hx.units[u].session_id for u in head] or []), []
        for u in mix:
            sid = hx.units[u].session_id
            if sid not in seen:
                seen.add(sid)
                firsts.append(u)
        mix = firsts[: p.get("div_n", 99)] + mix
    order = list(dict.fromkeys(head + mix))
    k = 99
    if p.get("oq_cap"):
        k = max(len(cite) + p.get("oq_extra", 2), (n or 0) + 1)
    passages, included, _ = build_pack(q, hx, order, budget=p.get("budget_other", sp["budget_other"]),
                                       window=sp.get("window_other", 0), order="chrono", max_sessions=k)
    in_pack = {x.id for x in passages}
    cite = [s for s in cite if s in in_pack] or None
    best = rows[0]["ce"] if rows else -12.0
    abstain_p = round(E._sigmoid(-(best + 2.0) / 2.0), 3)
    return EvidencePack(question_id=q.question_id, variant=p.get("_variant", ""), route="temporal", passages=passages,
                        hint="", cite_plan=cite, abstain_p=abstain_p, included_turns=included, computed=None,
                        debug={"ranking": order, "spec": {"kind": "other"}, "route": "question_r3",
                               "n_expected": n, "head": head})


# ---------------------------------------------------------------------------------------------------------------------
# 3. order questions: sentence-level CE fill of the packed event sessions
# ---------------------------------------------------------------------------------------------------------------------
def order_fill(q, hx, pack, p: dict):
    from core.pack import build_pack

    events = ((pack.debug or {}).get("parse") or {}).get("events") or []
    if not events or not pack.passages:
        return pack
    sids = [x.id for x in pack.passages]
    cand = [u for u in hx.units if u.session_id in set(sids) and u.role == "user"]
    if not cand:
        return pack
    pin = []
    if p.get("ord_first"):        # dev gold turns are mostly the opening user turn of the event session
        for sid in sids:
            fu = next((u.uid for u in hx.units if u.session_id == sid and u.role == "user"), None)
            if fu is not None:
                pin.append(fu)
    sents, owner = [], []
    if p.get("ord_sent"):         # sentence-level: a unit scores as its best sentence
        for u in cand:
            for snt in E._SENT.split(u.text):
                if len(snt) > 20:
                    sents.append(snt)
                    owner.append(u.uid)
    for ev in events[:4]:
        ev_c = re.sub(r"\([^)]*\)", " ", ev)
        if p.get("ord_sent") and sents:
            ss = hx.rerank_texts(ev_c, sents)
            bu = {}
            for sc_, uid in zip(ss, owner):
                bu[uid] = max(bu.get(uid, -99.0), sc_)
            scores = [bu.get(u.uid, -99.0) for u in cand]
        else:
            scores = hx.rerank_texts(ev_c, [u.text for u in cand])
        best = sorted(zip(scores, [u.uid for u in cand]), reverse=True)
        per = {}
        for s, uid in best:
            if s < p.get("ord_thr", 0.0):
                break
            sid = hx.units[uid].session_id
            if per.get(sid, 0) >= p.get("ord_per", 2):
                continue
            per[sid] = per.get(sid, 0) + 1
            pin.append(uid)
    ranking = list((pack.debug or {}).get("ranking") or [])
    have = set(pack.included_turns or [])
    new = [u for u in dict.fromkeys(pin) if hx.units[u].turn_id not in have]
    if not new:
        return pack
    passages, included, _ = build_pack(q, hx, ranking, budget=p.get("ord_budget", 9000), window=1, order="chrono",
                                       hint=pack.hint, max_sessions=len(sids), pinned=new)
    pack.passages, pack.included_turns = passages, included
    pids = {x.id for x in passages}
    pack.cite_plan = [s for s in (pack.cite_plan or []) if s in pids] or pack.cite_plan
    pack.debug["ord_fill"] = new
    return pack


def build(q, hx, _variant: str = "", **params):
    p = {**_BASE, **params}
    ap = _A.VARIANTS[p["a_variant"]]
    src = ""
    if _A._use_a(q, ap):
        pack = _A.build(q, hx, _variant=p["a_variant"], **ap)
        src = f"a_gap:{p['a_variant']}"
        kind = ((pack.debug or {}).get("parse") or {}).get("kind")
        if kind == "gap" and pack.computed is None:
            comp = None
            if p.get("agree"):
                pack, comp = gap_agree(q, hx, pack, p)
            if comp is None and p.get("fbg"):
                pack, comp = gap_fbg(q, hx, pack, p)
            if comp is not None:
                src += "+b_fb"
        if p.get("ord_fill") and kind == "order":
            pack = order_fill(q, hx, pack, p)
    else:
        bp = {**_BM.VARIANTS[p["b_variant"]]}
        spec = E.parse_question(q.question)
        if (p.get("oq_head") or p.get("oq_cap")) and not spec["events"] and not _BM._GAP.search(q.question):
            pack = build_other3(q, hx, {**bp, **p})
            src = "b_r3:other3"
        else:
            pack = _BM.build(q, hx, _variant=p["b_variant"], **bp)
            src = f"b_merge:{p['b_variant']}"
    pack.variant = _variant
    pack.debug = {**(pack.debug or {}), "merged_r2_from": src, "r3_from": src}
    return pack
