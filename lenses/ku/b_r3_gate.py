"""KU lens B, round 3: a value-type gate for the ku hand-off on the ssu ROUTE (ku -> ssu misroutes are the biggest
routed loss: dev 25 q at S 77, dev200 9 q at S 55).

This file is a route lens for the ssu route (same contract as lenses/ssu/merged_r2.py, which it reuses unchanged):
  1. role_guess (SSA-B) >= 0.8 -> ssa lens            (merged_r2.choose, unchanged)
  2. ku_gate(q, hx) -> ku lens b_r2 r2b                (NEW: value-type gate, below)
  3. otherwise the ssu lens a_struct2 r3rn             (= v1)

ku_gate (r3) refines the r2 detector b_r2.ku_pair_p (distinct values + min pair score >= 6 + min cov >= 0.5), which
fired on 6 of 45 test ssu-routed questions with planted drift / sibling slots (sourdough name, R-77 capacitor / dial
lamp, birthday restaurant, move date, cafe). The gate adds:
  * typed values: both pair sentences must carry a value of the SAME type (number+unit / time / money / name) and
    those typed values must differ ('6:30 am' vs '7:00 am', '3 km' vs '5 km'); untyped capitalised-word drift does
    not count;
  * own statements: both pair members are the user's own (own > 0), not assistant recaps;
  * attribute head: both pair sentences contain the question's rarest content term (the attribute head), so sibling
    slots ('dial lamp' vs 'filter capacitor') do not pair;
  * (option) an update cue in the question (now / currently / previous / before / still / anymore / usually ...)
    or in the newer pair sentence (switched / changed / upgraded / no longer / now ...).
debug carries every feature (ku_feats) so the gate can be re-fit offline from per_question.jsonl.
"""
from __future__ import annotations

import re

from harness.sweep import load_lens
from lenses.ku import b_r2 as R2
from lenses.ku import b_semantic as B

_loaded: dict = {}


def _lens(path: str):
    if path not in _loaded:
        _loaded[path] = load_lens(path)
    return _loaded[path]


# --- typed values ------------------------------------------------------------------------------------------------
_NUMW = "|".join(B._NUMW)
_UNIT = (r"(?:km|kilomet\w*|miles?|mi|laps?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?|times?|"
         r"cups?|glasses|books?|pages?|chapters?|people|members?|employees?|hives?|beehives?|trees?|plants?|"
         r"followers?|subscribers?|gb|mb|tb|kg|lbs?|pounds?|kilos?|%|percent|dollars?|euros?|steps?|reps?|sets?|"
         r"sessions?|classes?|episodes?|rooms?|tractors?|cats?|dogs?|kids?|pieces?|items?|bottles?|v|volts?|"
         r"watts?|w|ohms?|µf|uf|mf|pf|mhz|khz|hz|ghz|inch\w*|feet|foot|ft|cm|mm|m)\b")
_TIME_RX = re.compile(r"\b\d{1,2}(?::\d{2})?\s?(?:am|pm|a\.m\.|p\.m\.)|\b\d{1,2}:\d{2}\b|\b(?:noon|midnight)\b", re.I)
_MONEY_RX = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?\s?(?:k|K|million|m)?|\b\d[\d,]*(?:\.\d+)?\s?(?:dollars|usd|eur|euros|"
                       r"pln|zł|£|€)", re.I)
_QTY_RX = re.compile(rf"\b(\d[\d,]*(?:\.\d+)?|{_NUMW})(?:\s|-)?(?:\w+\s){{0,2}}?{_UNIT}", re.I)
_FREQ_RX = re.compile(rf"\b(?:(?:{_NUMW}|\d+)\s+times?\s+(?:a|per|each)\s+(?:day|week|month|year)|once|twice|"
                      r"daily|weekly|biweekly|monthly|every\s+(?:day|other\s+day|week|other\s+week|month|"
                      r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|morning|evening|night))\b", re.I)
_DAY_RX = re.compile(r"\b(?:mondays?|tuesdays?|wednesdays?|thursdays?|fridays?|saturdays?|sundays?)\b", re.I)


def _norm_num(s: str) -> str:
    s = s.lower().replace(",", "")
    return str(B._W2N.get(s, s))


def typed_values(sent: str, question: str = "") -> dict[str, set[str]]:
    """{'time': {...}, 'money': {...}, 'qty': {...}, 'freq': {...}, 'day': {...}, 'name': {...}} of one sentence.
    'name' = quoted names + capitalised words not in the question (as b_semantic.values, minus numbers)."""
    out: dict[str, set[str]] = {}
    t = {re.sub(r"\s|\.", "", m.group(0).lower()) for m in _TIME_RX.finditer(sent)}
    if t:
        out["time"] = t
    mo = {re.sub(r"[^\d.k]", "", m.group(0).lower()) for m in _MONEY_RX.finditer(sent)}
    if mo:
        out["money"] = mo
    sent_nt = _TIME_RX.sub(" ", _MONEY_RX.sub(" ", sent))
    # '... three weeks ago' is a date reference, not a value of the attribute
    q = {_norm_num(m.group(1)) for m in _QTY_RX.finditer(sent_nt) if not re.fullmatch(r"20\d\d", m.group(1))
         and not re.match(r"\s*(?:ago|earlier|later|before|from now)\b", sent_nt[m.end():], re.I)}
    if q:
        out["qty"] = q
    f = {m.group(0).lower() for m in _FREQ_RX.finditer(sent_nt)}
    if f:
        out["freq"] = f
    d = {m.group(0).lower().rstrip("s") for m in _DAY_RX.finditer(sent) if m.group(0).lower() not in question.lower()}
    if d:
        out["day"] = d
    nm = {v for v in B.values(sent, question) if not re.match(r"[\d$]", v) and v not in B._W2N
          and not _DAY_RX.fullmatch(v)}
    if nm:
        out["name"] = nm
    return out


_UPD_Q = re.compile(r"\b(now|currently|current|right now|these days|still|anymore|any ?more|most recent(?:ly)?|latest|"
                    r"previous(?:ly)?|before|initially|originally|at first|used to|usually|so far|end(?:ed)? up|"
                    r"switch(?:ed)?|chang\w+|updat\w+|increas\w+|decreas\w+)\b", re.I)
_UPD_S = re.compile(r"\b(now|switched|changed|change|upgraded|downgraded|moved|increased|decreased|bumped|raised|"
                    r"reduced|cut (?:back|down)|dropped|no longer|anymore|instead|new|newly|recently|just|finally|"
                    r"started|stopped|went up|went down|up to|down to|from .{1,30} to|replaced|renamed|promoted|"
                    r"these days|lately|ended up|decided)\b", re.I)


def ku_gate(q, hx, need_type: bool = True, need_own: bool = True, need_head: bool = True, need_cue: bool = False,
            qtyped: bool = False, revert: bool = False, cue_old: bool = False, cue_min_score: float = 1.0,
            cue_min_cov: float = 0.3,
            min_score: float = 6.0, min_cov: float = 0.5, types: tuple = ("time", "money", "qty", "freq", "day"),
            **_) -> tuple[bool, dict]:
    """Value-type gate. Returns (hit, features)."""
    p = dict(R2.VARIANTS["r2b"])
    r = B.analyze(q, hx, **p)
    ok, f = R2.confidence(r, hx, q.question, dict(p, gate_v=2))
    if "pair_sc" not in f:
        return False, {"why": "single"}
    pair, bbs = r["pair"], r["best_by_sess"]
    so, sn = bbs[pair[0]], bbs[pair[1]]
    to, tn = typed_values(so["raw"], q.question), typed_values(sn["raw"], q.question)
    diff_types = sorted(k for k in set(to) & set(tn) if to[k] != tn[k] and not (to[k] & tn[k] and k == "name"))
    f["types_o"] = {k: sorted(v)[:4] for k, v in to.items()}
    f["types_n"] = {k: sorted(v)[:4] for k, v in tn.items()}
    f["diff_types"] = diff_types
    f["own"] = [so["own"], sn["own"]]
    f["asst"] = [bool(so.get("asst")), bool(sn.get("asst"))]
    # attribute head: rarest question content term (declarative form)
    qterms, idf = r["qterms"], r["idf"]
    head = max(qterms, key=lambda t: idf.get(t, 0)) if qterms else None
    f["head"] = head
    so_t, sn_t = set(B.content_terms(so["text"])), set(B.content_terms(sn["text"]))
    f["head_both"] = bool(head and head in so_t and head in sn_t)
    # top-2 rarest terms: both present in both sentences (stricter)
    top2 = sorted(qterms, key=lambda t: -idf.get(t, 0))[:2]
    f["head2_both"] = bool(top2) and all(t in so_t and t in sn_t for t in top2)
    f["cue_q"] = bool(_UPD_Q.search(q.question))
    f["cue_n"] = bool(_UPD_S.search(sn["raw"]))
    f["raw_o"], f["raw_n"] = so["raw"][:200], sn["raw"][:200]
    f["gap"] = hx.sess_by_id[pair[1]]["sess_idx"] - hx.sess_by_id[pair[0]]["sess_idx"]
    r2hit = bool(f["distinct"] and min(f["pair_sc"]) >= min_score and f["cov_min"] >= min_cov)
    f["r2hit"] = r2hit
    # qtyped: 'distinct' comes from the typed values below (b_semantic.values drops weekdays: Thursday -> Friday)
    hit = (min(f["pair_sc"]) >= min_score and f["cov_min"] >= min_cov) if qtyped else r2hit
    if need_type:
        hit = hit and any(t in diff_types for t in types)
    if need_own:
        hit = hit and so["own"] > 0 and sn["own"] > 0 and not so.get("asst") and not sn.get("asst")
    if need_head:
        hit = hit and f["head_both"]
    # r3 v2: the differing typed value must be of a type the QUESTION asks for, with disjoint values (an update
    # replaces the value), and neither pair sentence may be an abandoned trial
    qt = q_types(q.question)
    f["q_types"] = sorted(qt)
    f["qdiff"] = sorted(k for k in qt if k in to and k in tn and not (to[k] & tn[k]))
    f["revert"] = bool(REVERT.search(so["raw"]) or REVERT.search(sn["raw"]))
    if qtyped:
        hit = hit and bool(f["qdiff"])
    if revert:
        hit = hit and not f["revert"]
    # r3 v2b: the question itself asks about a change ('previous', 'before I ...', 'initially', 'more ... than',
    # 'increase or decrease': b_semantic mode old / compare / both) and both pair members are own, positive matches
    f["mode"] = r["mode"]
    f["cue_hit"] = bool(r["mode"] in ("old", "compare", "both") and min(f["pair_sc"]) >= cue_min_score
                        and f["cov_min"] >= cue_min_cov and so["own"] > 0 and sn["own"] > 0
                        and not so.get("asst") and not sn.get("asst") and not f["revert"])
    if cue_old:
        hit = hit or f["cue_hit"]
    if need_cue:
        hit = hit and (f["cue_q"] or f["cue_n"])
    f["hit"] = hit
    return hit, f


_BASE = {"ssu_lens": "lenses/ssu/a_struct2.py", "ssu_variant": "r3rn",
         "ssa_lens": "lenses/ssa/a_recsent.py", "ssa_variant": "r2_conf2",
         "ku_lens": "lenses/ku/b_r2.py", "ku_variant": "r2b", "thr": 0.8, "gate": None}
_G0 = dict(need_type=False, need_own=False, need_head=False)          # = r2 ku_pair_p (e5)
VARIANTS = {
    "v1": dict(_BASE),                                                  # = configs/best.json ssu route (no ku)
    "r2ku": dict(_BASE, gate=_G0),                                      # = e5 (r2 detector)
    "vt": dict(_BASE, gate=dict(need_type=True, need_own=True, need_head=True)),
    "vt_cue": dict(_BASE, gate=dict(need_type=True, need_own=True, need_head=True, need_cue=True)),
    "vt_nohead": dict(_BASE, gate=dict(need_type=True, need_own=True, need_head=False)),
    # r3 v2: question-typed value gate (q_types + disjoint typed values + no abandoned trial), relaxed score / cov
    "qt3": dict(_BASE, gate=dict(need_type=False, need_own=True, need_head=False, qtyped=True, revert=True,
                                 min_score=3.0, min_cov=0.25, distinct_any=True)),
    "qt3c": dict(_BASE, gate=dict(need_type=False, need_own=True, need_head=False, qtyped=True, revert=True,
                                  min_score=3.0, min_cov=0.25, cue_old=True)),
    # qt3c + abstain_p = min(ku lens, ssu lens) on hand-offs (pack and route identical to qt3c)
    "qt3c_ap": dict(_BASE, ap_min_ssu=True, gate=dict(need_type=False, need_own=True, need_head=False, qtyped=True,
                                                      revert=True, min_score=3.0, min_cov=0.25, cue_old=True)),
    "qt2": dict(_BASE, gate=dict(need_type=False, need_own=True, need_head=False, qtyped=True, revert=True,
                                 min_score=2.0, min_cov=0.25, distinct_any=True)),
    "qt4": dict(_BASE, gate=dict(need_type=False, need_own=True, need_head=False, qtyped=True, revert=True,
                                 min_score=4.0, min_cov=0.4, distinct_any=True)),
}


def build(q, hx, _variant: str = "", ssu_lens: str = "", ssu_variant: str = "", ssa_lens: str = "",
          ssa_variant: str = "", ku_lens: str = "", ku_variant: str = "", thr: float = 0.8, gate: dict | None = None,
          feats: bool = True, ap_min_ssu: bool = False, **_):
    merged = _lens("lenses/ssu/merged_r2.py")
    r, info = merged.choose(q, hx, thr=thr, ku_pair=False)
    if r == "ssu" and (gate is not None or feats):
        try:
            hit, f = ku_gate(q, hx, **(gate or _G0))
            info["ku_feats"] = f
            if gate is not None and hit:
                r = "ku"
        except Exception as exc:                       # a failing detector never changes the route
            info["ku_gate_error"] = repr(exc)[:200]
    path, v = {"ssa": (ssa_lens, ssa_variant), "ku": (ku_lens, ku_variant)}.get(r, (ssu_lens, ssu_variant))
    lens = _lens(path)
    pack = lens.build(q, hx, _variant=v, **lens.VARIANTS[v])
    if r == "ku" and ap_min_ssu and pack.abstain_p is not None:
        # the ku lens's phrase-level abstention signal is calibrated on ku-routed questions and runs high on these
        # hand-offs ('coffee-to-water ratio' 0.88); keep the lower of the two lenses' estimates (pack unchanged)
        try:
            sl = _lens(ssu_lens)
            ap_ssu = sl.build(q, hx, _variant=ssu_variant, **sl.VARIANTS[ssu_variant]).abstain_p
            if ap_ssu is not None:
                info["ap_ku"], info["ap_ssu"] = pack.abstain_p, ap_ssu
                pack.abstain_p = min(pack.abstain_p, ap_ssu)
        except Exception as exc:
            info["ap_error"] = repr(exc)[:200]
    pack.route = r
    pack.debug = {**(pack.debug or {}), "route_final": r, "inner_lens": path, "inner_variant": v, **info}
    return pack


# --- r3 v2: the question's expected value type + a reverted-trial filter -------------------------------------------
def q_types(question: str) -> set[str]:
    """Value types the question asks for. Names / titles / places are excluded on purpose: capitalised-word drift
    (sourdough name candidates, cafe / restaurant names) is the planted ssu decoy pattern, not an update signal."""
    ql = question.lower()
    out: set[str] = set()
    if re.search(r"\bwhat time\b|\bpersonal (?:best|record)\b|\b(?:best|finish(?:ing)?) time\b|\bwhen do i\b", ql):
        out |= {"time"}
    if re.search(r"\bhow (?:often|frequently)\b|\bhow many times\b|\bhow regularly\b", ql):
        out |= {"freq", "qty", "day"}
    if re.search(r"\b(?:what|which) days?\b|\bday of the week\b", ql):
        out |= {"day"}
    if re.search(r"\bhow (?:many|much|long|far|old)\b|\b(?:amount|number|value|voltage|wattage|price|cost|rent|"
                 r"salary|budget|limit|capacity|distance|weight|size|total)\b", ql):
        out |= {"qty", "money"}
    return out


# a later trial that was abandoned is not an update ('I briefly tried a 68 uF capacitor ... and I removed it',
# 'I bought a 12-volt lamp, but it was too dim')
REVERT = re.compile(r"\b(?:briefly|temporarily)\b|\b(?:tried|tested|test(?:ed)? out|tried out)\b[^.]{0,80}\bbut\b|"
                    r"\bbut\b[^.]{0,60}\b(?:too (?:dim|low|high|loud|quiet|weak|bright|small|big|large|slow|fast|"
                    r"expensive|noisy|hot)|didn'?t (?:keep|work|fit|last)|did not (?:keep|work|fit)|removed|"
                    r"returned it|took it (?:out|back)|went back|switched back|swapped back|reverted|gave up)\b",
                    re.I)
