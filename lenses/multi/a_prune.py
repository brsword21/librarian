"""Lens A round 2 ("Struktura") for multi-session: citation-robust packing on top of lens B (b_sweep deep8_10k).

ROUND 2 BEST: `r2best` (= p8x1_ddl1 + calibrated abstain_p). dev S 87.2 / Sall 84.0, dev200 S 83.2 / Sall 78.9
(B deep8_10k through this file, `b_ref`: 86.6 / 73.9 and 85.2 / 73.5). See a_report.md.

Problem (round 1): B's pack holds ~8 sessions on dev (8-17 on test) for 2-3 gold sessions. If Reactor cites every
passage we send, CF1 falls from 0.90 to ~0.47 (S 86.6 -> Sall 73.9).

Idea: decide the session set BEFORE packing. B scores every candidate unit with the cross-encoder (incl. every user
unit of the top-15 sessions); a session's strength is its best CE logit (out-of-window sessions are penalised when the
history spans the window). Then
  1. drop decoy sessions (question about me): the session's strongest units all report someone else's fact
     ("My friend Valentina bought tango shoes", "Carlos told me his systolic reading was 145") or decline the thing
     ("tried on ... but decided not to buy", "skipped buying", "did not use it in the R-77");
  2. core = sessions within `prune_d` (8) logits of the strongest one, at least 2, at most 14;
  3. one recall session (the next by strength) if it shares the question's topic words (a_tally.match_score >= 1);
  4. B's depth-first unit selection, rendering and hint inside the kept sessions; B's relative-CE cite plan.
Retrieval, scoring, rendering and the hint are B's (imported), so caches are shared and B's changes carry over.

abstain_p: B's signal noisy-OR the facet-absence check of lens A (lenses/multi/a_abstain.py) when `facet_w` > 0,
monotone-calibrated to P(unanswerable) when `calib` (fit on routed dev+dev200 multi).
Experimental (not recommended): `ledger` (code-extracted candidate sentences in the hint), `sent_ce`, `sent_extra`,
`prune_gap`, `lex_thr`.
"""
from __future__ import annotations

from core.types import EvidencePack
from lenses.multi import a_tally as T
from lenses.multi import b_sweep as B
from lenses.multi.a_abstain import combine, facet_absence

_BASE = dict(B.VARIANTS["deep8_10k"])
VARIANTS = {
    "b_ref": {**_BASE},
    "p8x1": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 20},
    "p8x1_f": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 20, "facet_w": 1.0},
    "p10x0m3": {**_BASE, "prune_d": 10.0, "prune_extra": 0, "prune_min": 3, "prune_max": 20},
    "p8x2": {**_BASE, "prune_d": 8.0, "prune_extra": 2, "prune_min": 2, "prune_max": 20},
    "p8x1L3": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 20, "lex_thr": 3.0,
               "extra_max": 3},
    "p6x1L3": {**_BASE, "prune_d": 6.0, "prune_extra": 1, "prune_min": 2, "prune_max": 20, "lex_thr": 3.0,
               "extra_max": 3},
    "p8x1_f5": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 20, "facet_w": 0.5},
    "p7x1": {**_BASE, "prune_d": 7.0, "prune_extra": 1, "prune_min": 2, "prune_max": 20},
    "p9x1": {**_BASE, "prune_d": 9.0, "prune_extra": 1, "prune_min": 2, "prune_max": 20},
    "p8x1m3": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 3, "prune_max": 20},
    "p8x1_14": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14},
    "p8x1_do": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14, "drop_other": True},
    # ROUND 2 BEST: prune to the CE core (top - 8 logits, 2..14 sessions) + 1 recall session, decoy sessions out,
    # abstain_p += facet absence (noisy-OR)
    "p8x1_dof": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14, "drop_other": True,
                 "facet_w": 1.0},
    "p8g4x1": {**_BASE, "prune_d": 8.0, "prune_gap": 4.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14,
               "drop_other": True, "facet_w": 1.0},
    "p8g5x1": {**_BASE, "prune_d": 8.0, "prune_gap": 5.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14,
               "drop_other": True, "facet_w": 1.0},
    "p12g4x0": {**_BASE, "prune_d": 12.0, "prune_gap": 4.0, "prune_extra": 0, "prune_min": 2, "prune_max": 14,
                "drop_other": True, "facet_w": 1.0},
    "p10x0": {**_BASE, "prune_d": 10.0, "prune_extra": 0, "prune_min": 2, "prune_max": 14,
              "drop_other": True, "facet_w": 1.0},
    "p8x1c4": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14, "drop_other": True,
               "facet_w": 1.0, "extra_if_core_lt": 4},
    "p8x1c5": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14, "drop_other": True,
               "facet_w": 1.0, "extra_if_core_lt": 5},
    "p8x1c4s": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14, "drop_other": True,
                "facet_w": 1.0, "extra_if_core_lt": 4, "sent_ce": True},
    "p8x1_dd": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14, "drop_other": True,
                "facet_w": 1.0, "drop_declined": True},
    "p8x1_ddl1": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14, "drop_other": True,
                  "facet_w": 1.0, "drop_declined": True, "extra_lex": 1.0},
    "p8x1_ddl1s2": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14, "drop_other": True,
                    "facet_w": 1.0, "drop_declined": True, "extra_lex": 1.0, "extra_scan": 2},
    "p8x1_ddl15": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14, "drop_other": True,
                   "facet_w": 1.0, "drop_declined": True, "extra_lex": 1.5},
    "p8x1_se2": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14, "drop_other": True,
                 "facet_w": 1.0, "drop_declined": True, "extra_lex": 1.0, "sent_extra": 2},
    # ROUND 2 BEST = p8x1_ddl1 + calibrated abstain_p
    "r2best": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14, "drop_other": True,
               "facet_w": 1.0, "drop_declined": True, "extra_lex": 1.0, "calib": True},
    "p8x1_led": {**_BASE, "prune_d": 8.0, "prune_extra": 1, "prune_min": 2, "prune_max": 14, "drop_other": True,
                 "ledger": True},
    "p6x1": {**_BASE, "prune_d": 6.0, "prune_extra": 1, "prune_min": 2, "prune_max": 20},
}


# Monotone calibration of the raw abstention score (B's signal noisy-OR facet absence) to P(unanswerable), fitted
# on the routed multi questions of dev + dev200 pooled (200 q, 19 unanswerable; isotonic bins <0.2: 6/155,
# 0.2-0.3: 3/25, 0.3-0.4: 2/6, >=0.4: 8/14). Ranking (AUC) is unchanged.
_CAL = [(0.0, 0.03), (0.15, 0.04), (0.25, 0.12), (0.35, 0.33), (0.45, 0.57), (1.0, 0.65)]


def calibrate(p: float) -> float:
    for (x0, y0), (x1, y1) in zip(_CAL, _CAL[1:]):
        if p <= x1:
            return y0 + (y1 - y0) * (p - x0) / (x1 - x0)
    return _CAL[-1][1]


def _sess_strength(hx, rr: dict, a: dict, win_active: bool, P: dict) -> dict[str, float]:
    """Best CE logit per session over all CE-scored units (users + short recaps, as B's cite rule), minus a penalty
    for sessions outside an engaged time window."""
    out: dict[str, float] = {}
    for u, sc in rr.items():
        unit = hx.units[u]
        if P["asst"] == "none" and unit.role != "user":
            continue
        if B._role_ok(unit, P["asst"]) <= 0:
            continue
        if win_active and a["window"]:
            wp = B.window_prior(unit.date.date(), a["window"], True)
            if wp < 1.0:
                sc = sc - P.get("win_pen", 4.0) * (1.0 - wp)
        sid = unit.session_id
        if sc > out.get(sid, -99.0):
            out[sid] = sc
    return out


import re as _re

# "Carlos told me his systolic reading was 145", "she said her ..." : reported facts of another person that B's
# agent_label misses (it needs 'told me that he' or 'my <kin> has')
_REPORT2 = _re.compile(r"\b(?:[A-Z][a-z]+|he|she|they)\s+(?:told me|said|mentioned|says|tells me)\s+(?:that\s+)?"
                       r"(?:his|her|their|he|she|they)\b")


# "Valentina made 7 kilos of dulce de leche", "Carlos has five grandchildren": a named third person as the subject
_NAMED_SUBJ = _re.compile(r"(?:^|[:;,.!?]\s+|\bnews:\s+|\band\s+)(?!I\b|I'|It\b|This\b|That\b|The\b|My\b|We\b)"
                          r"[A-Z][a-z]+\s+(?:just\s+|also\s+)?(?:made|bought|has|had|ate|read|got|spent|adopted|planted|"
                          r"harvested|ran|swam|added|opened|deposited|finished|owns)\b")


def _label(text: str, terms: list[str], base: str) -> str:
    if base == "other":
        return base
    ss = B.split_sents(text)
    idx = B.focus_sentences(text, terms)[:1]                 # the sentence with the most question terms
    if idx and all((_REPORT2.search(ss[i]) or _NAMED_SUBJ.search(ss[i]))
                   and not _re.search(r"\bI\s+(?:also|too|bought|got|had|was|did|made)\b", ss[i]) for i in idx):
        return "other"
    return base


def _sent_strength(q, hx, rr, strength, a, win_active, P) -> dict[str, float]:
    """Sentence-level CE: a fact is one sentence inside a chatty unit, and unit-level CE dilutes it. For the top
    sessions' best units, score each sentence on its own; session strength = max(unit CE, best sentence CE)."""
    top_s = sorted(strength, key=lambda s: -strength[s])[:P.get("sent_sess", 20)]
    by_s: dict[str, list[int]] = {}
    for u in sorted(rr, key=lambda x: -rr[x]):
        sid = hx.units[u].session_id
        if sid in top_s and hx.units[u].role == "user" and len(by_s.setdefault(sid, [])) < P.get("sent_units", 3):
            by_s[sid].append(u)
    sents, owner = [], []
    for sid, us in by_s.items():
        for u in us:
            for se in B.split_sents(hx.units[u].text):
                if len(se) >= 20:
                    sents.append(se)
                    owner.append((sid, u))
    out = dict(strength)
    if not sents:
        return out
    for (sid, u), sc in zip(owner, hx.rerank_texts(q.question, sents)):
        if win_active and a["window"]:
            wp = B.window_prior(hx.units[u].date.date(), a["window"], True)
            sc = sc - P.get("win_pen", 4.0) * (1.0 - wp)
        if sc > out.get(sid, -99.0):
            out[sid] = sc
    return out


# narrow "declined / not done" statements ("tried on ... but decided not to buy", "skipped buying"); B's _NEG is
# broader (need to / want to / didn't), so it is not used for dropping
_DECLINED = _re.compile(r"\b(?:decided not to|chose not to|skipped (?:buying|getting|the)|passed on|"
                        r"talked myself out of|didn'?t (?:end up )?(?:buy|get|use)(?:ing)?\b|but didn'?t buy|"
                        r"(?:didn'?t|did not) use it)", _re.I)


_DID = _re.compile(r"\bI(?:'ve)?\s+(?:\w+\s+){0,2}?(?:bought|got|made|ordered|spent|paid|picked up|added|replaced|"
                  r"used|purchased|splurged|attended|planted|adopted)\b", _re.I)


def _declined(text: str, terms: list[str]) -> bool:
    """The unit's main topical sentence declines the thing, and no other topical sentence of the unit affirms one."""
    ss = B.split_sents(text)
    idx = B.focus_sentences(text, terms)
    if not idx or not _DECLINED.search(ss[idx[0]]):
        return False
    return not any(_DID.search(ss[i]) and not _DECLINED.search(ss[i]) for i in idx[1:])


def _sent_extra(q, hx, a, taken: set, top: float, win_active: bool, P) -> list[str]:
    """Instance sentences buried in chatty units ('I'll check the roots today. I just finished reading a book about
    ...'): unit-level CE scores them ~-11. Take the user sentences with a strong lexical hit (a_tally.match_score),
    declarative, own (not reported / declined), outside the kept sessions; score each sentence alone with the CE and
    add the sessions whose sentence reaches the core's level (>= top - prune_d), at most `sent_extra` sessions."""
    qa = T.analyze(q.question, q.date)
    cands = []
    for u in hx.units:
        if u.role != "user" or u.session_id in taken:
            continue
        if win_active and a["window"] and B.window_prior(u.date.date(), a["window"], True) < 1.0:
            continue
        for se in T.sentences(u.text):
            if se.rstrip().endswith("?") or len(se) < 25:
                continue
            if T.match_score(se, qa) >= P.get("sent_lex", 2.5) and not _REPORT2.search(se) \
                    and B.agent_label(se, a["terms"]) != "other" and not _DECLINED.search(se):
                cands.append((u.session_id, se))
    if not cands:
        return []
    cands = cands[:P.get("sent_cap", 40)]
    best: dict[str, float] = {}
    for (sid, se), sc in zip(cands, hx.rerank_texts(q.question, [c[1] for c in cands])):
        best[sid] = max(best.get(sid, -99.0), sc)
    ok = sorted((s for s in best if best[s] >= top - P["prune_d"]), key=lambda s: -best[s])
    return ok[:P["sent_extra"]]


def _sess_lex(hx, q, sids: set) -> dict[str, float]:
    qa = T.analyze(q.question, q.date)
    out: dict[str, float] = {}
    for u in hx.units:
        if u.role != "user" or u.session_id not in sids:
            continue
        for se in T.sentences(u.text):
            m = T.match_score(se, qa)
            if m > out.get(u.session_id, 0.0):
                out[u.session_id] = m
    return out


def build(q, hx, **params) -> EvidencePack:
    P = dict(B.VARIANTS["sweep"])
    P.update(params)
    if not P.get("prune_d"):
        pack = B.build(q, hx, **params)
        if P.get("facet_w"):
            pf, why = facet_absence(q.question, q.date, hx)
            pack.abstain_p = combine(pack.abstain_p, pf, P["facet_w"])
            pack.debug["facet_why"] = why
        return pack

    a = B.analyze(q.question, q.date)
    terms = a["terms"] + [w for f in a["facets"] for w in B.content_terms(f)]
    ranked, final, rr, lab, facet_top, rest, win_active = B._score_units(q, hx, a, P)

    # abstention (B's signal, optionally + A's facet absence)
    miss = B.missing_terms(hx, a["terms"])
    miss_frac = len(miss) / max(1, len([w for w in a["terms"] if w not in B._GENERIC and not w.isdigit()]))
    top_rr = max(rr.values()) if rr else -10.0
    head = [u for u in ranked[:10] if B.focus_sentences(hx.units[u].text, a["terms"])]
    all_other = bool(head) and not a["others_ok"] and all(lab[u] == "other" for u in head[:6])
    abstain_p = B.abstain_prob(top_rr, miss_frac, all_other)
    why = []
    if P.get("facet_w"):
        pf, why = facet_absence(q.question, q.date, hx)
        abstain_p = combine(abstain_p, pf, P["facet_w"])
    raw_p = abstain_p
    if P.get("calib"):
        abstain_p = calibrate(raw_p)
    hint = B.build_hint(a, q.date, B.abstain_prob(top_rr, miss_frac, all_other))   # hint unchanged vs B

    # 1) session set: strong CE sessions + a few recall sessions
    strength = _sess_strength(hx, rr, a, win_active, P)
    if P.get("sent_ce"):
        strength = _sent_strength(q, hx, rr, strength, a, win_active, P)
    order = sorted(strength, key=lambda s: -strength[s])
    dropped = []
    if P.get("drop_other") and not a["others_ok"]:
        # a session whose strongest units all report someone else's fact ("Carlos told me his systolic reading was
        # 145", "my friend Valentina bought tango shoes") is a decoy for a question about me: keep it out of the pack
        by_s: dict[str, list[int]] = {}
        for u in rr:
            by_s.setdefault(hx.units[u].session_id, []).append(u)
        for sid in order[:P.get("prune_max", 20) + 5]:
            top_u = [u for u in by_s.get(sid, []) if rr[u] >= strength[sid] - P.get("drop_band", 2.0)
                     and hx.units[u].role == "user"]
            if top_u and all(_label(hx.units[u].text, a["terms"], lab.get(u, "none")) == "other" for u in top_u):
                dropped.append(sid)
            elif (P.get("drop_declined") and top_u and not _re.search(r"\b(not|skip|decid|declin|tried|almost)",
                                                                      q.question, _re.I)
                  and all(_declined(hx.units[u].text, a["terms"]) for u in top_u)):
                dropped.append(sid)
        order = [s for s in order if s not in dropped]
    top = strength[order[0]] if order else -99.0
    core = []
    for i, sid in enumerate(order):
        if strength[sid] < top - P["prune_d"]:
            break
        # a big drop in CE strength separates the instance sessions from topical chatter (test: 5 'systolic reading'
        # sessions at -1.8..-3.9, then -9.1)
        if P.get("prune_gap") and i >= P.get("prune_min", 2) and strength[order[i - 1]] - strength[sid] >= P["prune_gap"]:
            break
        core.append(sid)
    core = core[:P.get("prune_max", 20)]
    if len(core) < P.get("prune_min", 2):
        core = order[:P.get("prune_min", 2)]
    rest_s = [s for s in order if s not in core]
    n_extra = P.get("prune_extra", 0)
    if P.get("extra_if_core_lt") and len(core) >= P["extra_if_core_lt"]:
        n_extra = 0                     # a large CE core already spans the instances; the recall slot is for small cores
    if P.get("extra_lex") is not None and n_extra:
        # the recall slot goes to a session that at least shares the question's topic words (a_tally.match_score)
        cand = rest_s[:P.get("extra_scan", 1)]
        lx = _sess_lex(hx, q, set(cand))
        extra = [sid for sid in cand if lx.get(sid, 0.0) >= P["extra_lex"]][:n_extra]
    else:
        extra = rest_s[:n_extra]
    if P.get("lex_thr"):
        # recall by lexical evidence (lens A): a session outside the CE core whose best user sentence carries the
        # question's topic words / category instances / attribute pattern (a_tally.match_score) is an instance candidate
        lex = _sess_lex(hx, q, set(rest_s[:P.get("lex_scan", 30)]))
        extra += [s for s in rest_s if s not in extra and lex.get(s, 0.0) >= P["lex_thr"]]
        extra = extra[:P.get("extra_max", 3)]
    if P.get("sent_extra"):
        extra += _sent_extra(q, hx, a, set(core) | set(extra) | set(dropped), top, win_active, P)
    keep = set(core) | set(extra)

    # 2) B's depth-first selection restricted to the kept sessions
    ranked_k = [u for u in ranked if hx.units[u].session_id in keep]
    facet_k = {f: [u for u in us if hx.units[u].session_id in keep] for f, us in facet_top.items()}
    P2 = dict(P)
    if P.get("prune_per_sess"):
        P2["per_sess"] = P["prune_per_sess"]
    picks = B._select(hx, ranked_k, facet_k, P2)
    if P.get("ledger"):
        P2["budget"] = P["budget"] - P.get("ledger_reserve", 1500)
    passages, included, chars, chosen = B._pack_trimmed(q, hx, picks, hint, P2, terms)
    in_pack = {p.id for p in passages}
    ledger = []
    if P.get("ledger") and passages:
        ledger = _ledger(q, hx, passages, chosen, a, P)
        if ledger:
            hint = (hint + " Candidate statements found by search, one per excerpt (check each against the excerpt and "
                    "the question's conditions; not all may qualify, and some instances may be missing): "
                    + " | ".join(ledger))
            from core.pack import message_chars
            chars = message_chars(q, passages, hint)

    # 3) cite plan: B's relative CE rule over the packed sessions
    rmax = {s: strength[s] for s in in_pack if s in strength}
    corder = sorted(rmax, key=lambda s: -rmax[s])
    ctop = rmax[corder[0]] if corder else -99.0
    cite = [s for s in corder if rmax[s] >= ctop - P.get("cite_d", 4.0)][:P.get("cite_max", 6)]
    if len(cite) < 2:
        cite = corder[:2]
    if P.get("cite_all"):
        cite = sorted(in_pack, key=lambda s: hx.sess_by_id[s]["sess_idx"])

    return EvidencePack(question_id=q.question_id, variant=params.get("_variant", ""), route="multi",
                        passages=passages, hint=hint, cite_plan=cite or None, abstain_p=abstain_p,
                        included_turns=included, computed=None,
                        debug={"ranking": ranked + rest, "window_active": win_active, "top_rr": top_rr,
                               "abstain_raw": round(raw_p, 3),
                               "missing_terms": miss, "facet_why": why, "chars": chars,
                               "strength": {s: round(strength[s], 2) for s in order[:25]},
                               "core": core, "extra": extra, "dropped_other": dropped, "ledger": ledger})


def _ledger(q, hx, passages, chosen, a, P) -> list[str]:
    """One line per packed session: '[E#] date: <best own sentence>' (CE on the question-term sentences of its packed
    user units). Sentences reporting someone else's fact are skipped; weak sessions (best < top - ledger_d) too."""
    rows = []
    for n, p in enumerate(passages, 1):
        sents = []
        for u in chosen.get(p.id, []):
            unit = hx.units[u]
            if unit.role != "user":
                continue
            ss = B.split_sents(unit.text)
            for j in B.focus_sentences(unit.text, a["terms"])[:3]:
                if (ss[j] not in sents and not ss[j].rstrip().endswith("?") and not _REPORT2.search(ss[j])
                        and B.agent_label(ss[j], a["terms"]) != "other"):
                    sents.append(ss[j])
        if not sents:
            continue
        # statements of a dated / quantified own event beat topical chatter ("great list of questions for my doctor")
        sc = [x + (2.0 if B._FACT.search(se) else 0.0) for x, se in zip(hx.rerank_texts(q.question, sents), sents)]
        k = max(range(len(sents)), key=lambda i: sc[i])
        rows.append((sc[k], n, p.date[:10].replace("/", "-"), sents[k]))
    if not rows:
        return []
    top = max(r[0] for r in rows)
    keep = [r for r in rows if r[0] >= top - P.get("ledger_d", 6.0)][:P.get("ledger_max", 12)]
    out = []
    for _, n, d, se in sorted(keep, key=lambda r: r[1]):
        se = se if len(se) <= 180 else se[:177].rsplit(" ", 1)[0] + " …"
        out.append(f"[E{n}] {d}: {se}")
    return out
