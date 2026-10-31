"""KU lens A, round 2: citation-robust packing on top of the round-1 attribute timeline (lenses/ku/a_timeline.py).

Round 1 packed the cited pair [older, newest] plus 2 backup sessions (1 unit each). If Reactor cites every passage
(post-filtering by cite_plan is not confirmed), the 2 backups cost ~0.3 CF1 (Sall 83 vs S 92). Round 2:
- `extra_gate`: backup sessions only when the pair is NOT confident (no own older mention, the newest is a low
  coverage / admitted / assistant mention, or a strong own mention competes with the newest).
- the timeline hint still quotes the dated backup mentions, so Reactor sees them without a citable passage.
- the budget freed by dropping backups goes to more context of the two cited sessions (`pair_units`, `window`).
- `abstain_p(q, hx)` is exported for the routed KU lens (brief item 3).
"""
from __future__ import annotations

import re

from core.types import EvidencePack
from lenses.ku import a_timeline as T

_B2 = dict(T._PK, retr="hybrid", dense_user=True, admit_k=3, admit_bonus=0.2)   # round-1 best (pkd_b2)
VARIANTS = {
    "r1_b2": dict(_B2),                                   # reference: round-1 pkd_b2 through this build()
    "e0": dict(_B2, extra=0),                             # pair only
    "e0_b3": dict(_B2, extra=0, budget=3000),            # pair only, smaller budget
    "gate": dict(_B2, extra=2, extra_gate=True),          # backups only when the pair is not confident
    "gate1": dict(_B2, extra=1, extra_gate=True),
    # sentence cross-encoder gate: own mentions whose CE logit is far below the best own mention cannot be the
    # newest / older value ("Six people is solid for summer" for "UX team", "upgraded my PC to an SSD" for "vehicle")
    "ce3": dict(_B2, extra=0, ce_gate=3.0),
    "ce5": dict(_B2, extra=0, ce_gate=5.0),
    "ce7": dict(_B2, extra=0, ce_gate=7.0),
    "cen3": dict(_B2, extra=0, ce_gate=3.0, ce_mode="newest"),
    "cen5": dict(_B2, extra=0, ce_gate=5.0, ce_mode="newest"),
    "cen7": dict(_B2, extra=0, ce_gate=7.0, ce_mode="newest"),
    "cenp5": dict(_B2, extra=0, ce_gate=5.0, ce_mode="newest", ce_protect=True),
    "cenp7": dict(_B2, extra=0, ce_gate=7.0, ce_mode="newest", ce_protect=True),
    # protection also for name-link updates ("Marta ... referred me to Bruno"), and a restatement must stay within 10
    # CE logits of the best own mention ("upgrade my laptop's RAM from 8GB to 16GB" is not the mobile plan)
    "cenq5": dict(_B2, extra=0, ce_gate=5.0, ce_mode="newest", ce_protect=True, ce_protect_link=True,
                  ce_protect_gap=10.0),
    # + "the lecturer's job" -> other owner; + request penalty ("I'd like to know more about the role of ...")
    "cenq5_dp": dict(_B2, extra=0, ce_gate=5.0, ce_mode="newest", ce_protect=True, ce_protect_link=True,
                     ce_protect_gap=10.0, det_poss=True),
    "cenq5_rq": dict(_B2, extra=0, ce_gate=5.0, ce_mode="newest", ce_protect=True, ce_protect_link=True,
                     ce_protect_gap=10.0, det_poss=True, req_pen=True),
    "cenq5_nq": dict(_B2, extra=0, ce_gate=5.0, ce_mode="newest", ce_protect=True, ce_protect_link=True,
                     ce_protect_gap=10.0, det_poss=True, no_req=True),
}


# ------------------------------------------------------------------------------------------------------------------
def pair_confidence(spec, tl, mentions) -> tuple[bool, list[str]]:
    """Is the cited pair [older, newest] reliable enough to send it alone? Returns (confident, reasons)."""
    why = []
    nw, od = tl.newest, tl.older
    if nw is None:
        return False, ["no newest"]
    if od is None or od.session_id == nw.session_id:
        why.append("no older")
    if nw.owner != "self":
        why.append("newest not own")
    if getattr(nw, "admitted", False):
        why.append("newest admitted")
    if nw.role == "assistant":
        why.append("newest assistant")
    if nw.cov < 0.5:
        why.append(f"newest cov {nw.cov:.2f}")
    # a strong own mention LATER than the newest that was not taken (need_val / strong filter) -> doubt
    later = [m for m in tl.self_m if m.sort_key > nw.sort_key and m.score >= 0.85 * nw.score]
    if later:
        why.append("later strong mention")
    return not why, why


def _timeline(mentions, spec, p):
    return T.build_timeline(mentions, strong=p.get("strong", 0.75), rel=p.get("rel", 0.7),
                            older_mode=p.get("older_mode", "recent3"), cont=p.get("cont", False),
                            cont_cov=p.get("cont_cov", 0.4),
                            need_val=p.get("need_val", False) and spec.atype in ("number", "time", "duration", "freq",
                                                                                 "day"),
                            link=p.get("link", False), admit_old=p.get("admit_old", False),
                            cont_hits=p.get("cont_hits", 1))


_FIRST_PERSON = re.compile(r"\b(?:I|I'm|I’m|I've|I’ve|I'd|my|me|we|our|we're|we've)\b|\byou(?:r)?\b(?=.*\b(?:mention|said|told|now)\b)",
                           re.I)


_DET_POSS = re.compile(r"\b(?:the|a|an|his|her|their|its)\s+([a-z][\w\-]+)['’]s\s+([a-z][\w\-]+)", re.I)


def det_possessor(spec, mentions) -> int:
    """'it's the lecturer's job', 'a client's budget': the attribute word is owned by a noun phrase the question does
    not name -> another owner (round-1 ownership only knew relatives, friends and capitalised names)."""
    n = 0
    ql = spec.text.lower()
    for m in mentions:
        if m.owner != "self" or m.role != "user":
            continue
        for g in _DET_POSS.finditer(m.sent):
            owner, attr = g.group(1).lower(), T._stem([g.group(2).lower()])[0]
            if owner in ql or not (attr in spec.key or any(attr in a for a in spec.alts.values())):
                continue
            m.owner, m.score = "other", m.score - 0.6
            n += 1
            break
    return n


def no_value_requests(mentions) -> int:
    """A request or a pure question ("I'd like to know more about the role of a Marketing Director", "Do you have
    any tips ...?") does not state the user's value: it may not be the newest / older value (it stays for packing)."""
    n = 0
    for m in mentions:
        if m.owner == "self" and m.role == "user" and (T._REQUEST.match(m.sent)
                                                       or (m.sent.rstrip().endswith("?") and T._PURE_Q.match(m.sent))):
            m.owner = "query"
            n += 1
    return n


def ce_gate(q, hx, spec, mentions, tl, p, dbg):
    """Sentence-level cross-encoder check on the user's own mentions (lens B's idea, used here only as a gate):
    mentions whose CE logit is more than `ce_gate` below the best own mention are dropped, then the timeline is
    rebuilt with the same rules."""
    own = [m for m in mentions if m.owner == "self"]
    if len(own) < 2:
        return mentions, tl
    try:
        ce = hx.rerank_texts(q.question, [m.sent for m in own])
    except Exception as e:  # model server down -> no gate
        dbg["fallback"] = f"rerank_texts: {e!r}"[:200]
        return mentions, tl
    for m, c in zip(own, ce):
        m.ce = c
    top = max(ce)
    cut = top - p["ce_gate"]
    keep = [m for m in mentions if m.owner != "self" or m.ce >= cut]
    dbg["ce_top"] = round(top, 2)
    dbg["ce_dropped"] = sum(1 for m in own if m.ce < cut)
    tl2 = _timeline(keep, spec, p)
    if p.get("ce_mode") != "newest" or tl2.newest is None or tl.newest is None:
        return keep, tl2
    # newest-only mode: the gate may only veto the newest; packing keeps every mention, and the round-1 older value
    # stays unless it is not earlier than the new newest
    if tl2.newest is tl.newest:
        return mentions, tl
    later = tl.newest.sort_key > tl2.newest.sort_key
    restate = (later and T.same_kind(tl2.newest, tl.newest) and _FIRST_PERSON.search(tl.newest.sent)
               and getattr(tl.newest, "ce", top) >= top - p.get("ce_protect_gap", 99.0))
    named = later and p.get("ce_protect_link") and T.names_update(tl2.newest, tl.newest)
    if p.get("ce_protect") and (restate or named):
        # a first-person restatement of the same quantity ("I think I'm close to 1300 now" after "1250 followers")
        # keeps its place even with a low CE score; "Six people is solid for summer" has no first-person marker
        dbg["ce_protected"] = True
        return mentions, tl
    older = tl.older if (tl.older is not None and tl.older.sort_key < tl2.newest.sort_key
                         and tl.older.session_id != tl2.newest.session_id) else tl2.older
    dbg["ce_newest_changed"] = True
    return mentions, T.Timeline(tl.self_m, tl.other_m, tl2.newest, older)


def abstain_p(q, hx, variant: str = "e0") -> float:
    """Probability that the history does not contain the answer (round-1 timeline signals + missing phrases)."""
    p = {**VARIANTS[variant]}
    spec, ranking, mentions, tl, dbg = T.analyse(q, hx, p)
    ap, *_ = T.abstain_prob(spec, hx, tl, mentions, p.get("bigram_w", 0.0))
    return round(ap, 3)


def build(q, hx, **params) -> EvidencePack:
    p = dict(params) if "retr" in params else {**VARIANTS["e0"], **params}
    spec, ranking, mentions, tl, dbg = T.analyse(q, hx, p)
    ap, absent_all, absent_user, best_cov = T.abstain_prob(spec, hx, tl, mentions, p.get("bigram_w", 0.0))
    if p.get("no_req") and no_value_requests(mentions):
        tl = _timeline(mentions, spec, p)
    if p.get("det_poss") and det_possessor(spec, mentions):
        tl = _timeline(mentions, spec, p)
        dbg["det_poss"] = True
    if p.get("ce_gate"):
        mentions, tl = ce_gate(q, hx, spec, mentions, tl, p, dbg)

    pair = [m.session_id for m in (tl.older, tl.newest) if m is not None] if tl.newest is not None else []
    pair = list(dict.fromkeys(pair))
    if len(pair) < 2:
        for uid in ranking:
            sid = hx.units[uid].session_id
            if sid not in pair:
                pair.append(sid)
            if len(pair) >= 2:
                break

    conf, why = pair_confidence(spec, tl, mentions)
    n_extra = p.get("extra", 2)
    if p.get("extra_gate") and conf:
        n_extra = 0

    hint = T.make_hint(spec, tl, p.get("hint", "timeline"), absent_all, absent_user)
    groups = [(sid, T._sess_units(hx, sid, mentions, ranking, p.get("pair_units", 3))) for sid in pair]
    backup: list[str] = []
    for m in sorted(tl.self_m, key=lambda m: -m.score):
        if m.session_id not in pair and m.session_id not in backup:
            backup.append(m.session_id)
    for uid in ranking[:60]:
        sid = hx.units[uid].session_id
        if sid not in pair and sid not in backup:
            backup.append(sid)
    groups += [(sid, T._sess_units(hx, sid, mentions, ranking, 1)) for sid in backup[:n_extra]]
    w = p.get("window", 1)
    fill = [n for _, us in groups[: len(pair)] for u in us for n in hx.neighbors(u, w, w)] if w else []
    passages, included, chars = T.assemble(q, hx, groups, fill, p.get("budget", 4000), hint)
    ids = {ps.id for ps in passages if ps.id}
    cite = [s for s in sorted(pair, key=lambda s: hx.sess_by_id[s]["date"]) if s in ids] or None

    computed = None
    if (spec.direction == "latest" and spec.atype == "number" and tl.newest is not None and len(tl.newest.vals) == 1
            and not tl.newest.delta):
        computed = tl.newest.vals[0]

    dbg.update({"ranking": ranking[:300], "atype": spec.atype, "direction": spec.direction, "key": spec.key,
                "best_cov": round(best_cov, 3), "absent_all": absent_all, "absent_user": absent_user,
                "confident": conf, "why": why, "n_extra": n_extra,
                "timeline": [(m.date_str[:10], m.role, m.owner, round(m.score, 2), m.vals[:3], T._quote(m.sent, 90))
                             for m in tl.self_m[-6:]],
                "other": [(m.date_str[:10], T._quote(m.sent, 80)) for m in tl.other_m[:4]],
                "pair": pair, "chars": chars,
                "newest_sent": tl.newest.sent if tl.newest else None, "older_sent": tl.older.sent if tl.older else None,
                "newest_vals": tl.newest.vals if tl.newest else None})
    return EvidencePack(question_id=q.question_id, variant=params.get("_variant", ""), route="ku",
                        passages=passages, hint=hint, cite_plan=cite, abstain_p=round(ap, 3),
                        included_turns=included, computed=computed, debug=dbg)
