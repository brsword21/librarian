"""SSA-B round 3: one combined role detector + a hint guard for ssa questions that stay on the ssu route.

1. role_guess(q, hx) -> p_assistant (same signature as lenses/ssa/b_role.py, drop-in for the route wrappers
   lenses/ssu/merged_r2.py and lenses/multi/merged_r2.py via their `role_module` parameter).
   z = 0.35 * clip(d, -8, 8) + 2.2 * nf0 - 1.2           (B r2: cross-encoder margin best-assistant - best-user unit
                                                           in the CE-reranked hybrid top 40 + "no first-person word")
     + logit(pA) - 0.5                                    (A r2 lexical role scan, lenses/ssa/a_recsent.role_features:
                                                           BM25 assistant-vs-user top score, top-5 BM25 role mix,
                                                           question-term coverage per role in the best BM25 session,
                                                           first-person count, "should I" advice cue)
   p = sigmoid(z). The two signals fail on different questions: the CE margin is near 0 when the assistant's answer
   echoes the user's words ("Besides 'sexual compulsions', what were the other four alternative terms?", d = -0.3),
   while A's lexical scan sees that the question terms live in assistant turns (pA 0.87).
   Thresholds unchanged (ssu route 0.8, multi route 0.9). Offline over every router-placed question
   (scratch_b/r3_probe.py, r3_eval in b_report.md):
       dev    ssu   TP 37 -> 39 / 50, FP 0 (margin to the best non-ssa question 0.75 -> 0.54 logit)
       dev    multi TP  5 ->  6 /  6, FP 0 (margin 0.60 -> 1.24)
       dev200 ssu   TP  6 ->  6 /  7, FP 0;  multi TP 2 -> 2 / 2, FP 0
       test   ssu / multi firings: 0 / 0 (all test ssu / multi questions say I / my / our).
   Never used on the ku / temporal routes (FP there with both the old and the new score).

2. Hint guard (ssu route only): a gold-ssa question that stays on the ssu route gets the ssu lens' ownership hint
   "Answer from what the user said about their own X. Mentions of other people's ... are not the answer." The real
   Reactor calibration (runs/reactor/e1 results, q_73a1f68b2421 "Which company does a great job with environmentally
   responsible supply chains?", r1 pack, correct session in the pack) answered INSUFFICIENT_EVIDENCE because of it.
   When the question has no first-person word and p_assistant >= soft (0.6 by default), the guard removes the
   ownership sentence, the "not the user's own" decoy notes and any "the user never mentions" line, and states that
   the answer may be something the assistant said. The pack itself is unchanged.
   Fires on dev: 6 ssa + 1 ssu question ("How long did it take to move to the new apartment?", which only loses the
   ownership sentence); dev200: 1 ssa + 1 ssu; test: 0.

3. Advice hand-off (ssu route only, variant comb_guard_adv): "should I ..." questions ask for the assistant's advice,
   so they go to the ssa lens (a_recsent recqs_cf7, the session-filling hand-off target A recommends) at p >= 0.5.
   dev: "Which back-end languages should I learn for back-end development?" S 29 -> 93; no other question on the
   ssu route of dev / dev200 / test has the cue.

Measured (tag r3-ssa-b; S identical elsewhere, every test pack unchanged against runs/final/v1_test_packs.jsonl):
   ssu-routed dev 86.1 -> 86.6 (comb_guard_adv), dev200 82.3 -> 82.3; multi-routed dev 86.3 -> 86.7, dev200 tie;
   gold ssa through the router dev 91.8 -> 92.5 (comb) / 93.0 (comb_guard_adv), dev200 93.7 -> 93.7.
   Whole routed system (all questions): dev 85.9 -> 86.2 (Sall 84.7 -> 85.0), dev200 84.9 -> 84.9 (Sall 83.2).
Integration: routes.ssu = {"lens": "lenses/ssa/b_r3_role.py", "variant": "comb_guard_adv"} and
   routes.multi.params = {"role_module": "lenses/ssa/b_r3_role.py"}. Test diff: 0 of 90 ssu / multi / ssa packs
   (harness.audit --compare runs/final/v1_test_packs.jsonl); ku / temporal untouched.

VARIANTS (this file is also a routed lens: text router -> configs/best.json, with the ssu / multi route wrappers
pointed at this role_guess). Sweep with --route --type ssu / multi, or on all questions.
"""
from __future__ import annotations

import json
import math
import re

from core.paths import ROOT
from core.router import route

_FIRST = re.compile(r"\b(I|my|me|mine|I'm|I've|I'd|I'll|myself|our|ours|us)\b", re.I)

VARIANTS = {
    # control: configs/best.json exactly (role_guess from lenses/ssa/b_role.py)
    "v1": {"role_module": "lenses/ssa/b_role.py", "guard": False},
    # combined detector on the ssu / multi wrappers
    "comb": {"role_module": "lenses/ssa/b_r3_role.py", "guard": False},
    # combined detector + hint guard on the ssu route
    "comb_guard": {"role_module": "lenses/ssa/b_r3_role.py", "guard": True, "soft": 0.6},
    # B detector + hint guard only (isolates the guard)
    "v1_guard": {"role_module": "lenses/ssa/b_role.py", "guard": True, "soft": 0.6},
    # comb_guard + "should I" advice questions on the ssu route hand off to the ssa lens at p >= 0.5
    "comb_guard_adv": {"role_module": "lenses/ssa/b_r3_role.py", "guard": True, "soft": 0.6, "adv_thr": 0.5},
}

_W_A = 1.0      # weight of logit(pA)
_C = -0.5       # offset added with the A term


def _sig(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def role_features(q, hx) -> dict:
    from lenses.ssa import a_recsent as A
    from lenses.ssa import b_role as B
    fb = B.role_features(q, hx)
    fa = A.role_features(q, hx)
    zb = 0.35 * max(-8.0, min(8.0, fb["d"])) + 2.2 * (fb["n_first"] == 0) - 1.2
    z = zb + _W_A * _logit(fa["p_assistant"]) + _C
    return {"d": fb["d"], "n_first": fb["n_first"], "pA": fa["p_assistant"], "zB": zb, "z": z, "p": _sig(z)}


def role_guess(q, hx) -> float:
    """p_assistant: probability that the question asks about something the ASSISTANT said (see module docstring)."""
    return role_features(q, hx)["p"]


# ---------------------------------------------------------------------------------------------------------------------
# hint guard
# ---------------------------------------------------------------------------------------------------------------------
_OWN = re.compile(r"Answer from what the user said about their .*?are not the answer\.\s*", re.S)
_DECOY = re.compile(r"Note: the [^\n]*?, not the user's own\.\s*")
_NEVER = re.compile(r"The user never mentions [^\n]*?INSUFFICIENT_EVIDENCE\.\s*|If no passage states it for the user, "
                    r"answer INSUFFICIENT_EVIDENCE\.\s*")
GUARD_LINE = ("The answer may be something the assistant said in the conversation (a fact, list item or "
              "recommendation it gave), not only the user's own words.")


def guard_hint(hint: str) -> str:
    h = _OWN.sub("", hint or "")
    h = _DECOY.sub("", h)
    h = _NEVER.sub("", h)
    return (GUARD_LINE + (" " + h.strip() if h.strip() else "")).strip()


_loaded: dict = {}


def _lens(path: str):
    if path not in _loaded:
        from harness.sweep import load_lens
        _loaded[path] = load_lens(path)
    return _loaded[path]


_WRAPPERS = ("lenses/ssu/merged_r2.py", "lenses/multi/merged_r2.py")
# The v1 route lenses for ssu / multi (configs/best.json, frozen). Used directly so that this file can itself be put
# on the ssu (or multi) route of a config without calling itself.
_INNER = {"ssu": {"lens": "lenses/ssu/merged_r2.py", "variant": "role8_r3rn"},
          "multi": {"lens": "lenses/multi/merged_r2.py", "variant": "tight_role9"}}
_SELF = "lenses/ssa/b_r3_role.py"


_ADVICE = re.compile(r"\bshould I\b", re.I)


def build(q, hx, _variant: str = "", role_module: str = "lenses/ssa/b_role.py", guard: bool = False,
          soft: float = 0.6, config: str = "configs/best.json", adv_thr: float = 9.0,
          adv_lens: str = "lenses/ssa/a_recsent.py", adv_variant: str = "recqs_cf7", **_):
    cfg = json.loads((ROOT / config).read_text())
    r = route(q.question)[0]
    spec = _INNER.get(r) or cfg["routes"].get(r) or cfg["fallback"]
    if spec["lens"] == _SELF:
        spec = cfg["fallback"]
    lens = _lens(spec["lens"])
    params = {**lens.VARIANTS[spec["variant"]], **spec.get("params", {})}
    if spec["lens"] in _WRAPPERS:
        params["role_module"] = role_module
    pack = lens.build(q, hx, _variant=spec["variant"], **params)
    dbg = dict(pack.debug or {})
    final = dbg.get("route_final", pack.route or r)
    if adv_thr <= 1.0 and final == "ssu" and _ADVICE.search(q.question):
        # "should I ..." asks for the assistant's advice: hand off at a lower threshold (A r2 nf50a idea)
        try:
            p = dbg.get("p_assistant")
            if p is None:
                p = _lens(role_module).role_guess(q, hx)
            if p >= adv_thr:
                sl = _lens(adv_lens)
                pack = sl.build(q, hx, _variant=adv_variant, **sl.VARIANTS[adv_variant])
                dbg = {**dbg, **(pack.debug or {}), "advice_handoff": round(p, 4)}
                final = "ssa"
        except Exception as exc:
            dbg["advice_error"] = repr(exc)[:200]
    if guard and final == "ssu" and not _FIRST.search(q.question):
        try:
            p = dbg.get("p_assistant")
            if p is None:
                p = _lens(role_module).role_guess(q, hx)
            if p >= soft:
                pack.hint = guard_hint(pack.hint)
                dbg["hint_guard"] = round(p, 4)
        except Exception as exc:                                 # the guard never breaks a pack
            dbg["guard_error"] = repr(exc)[:200]
    pack.route = final
    pack.variant = _variant
    pack.debug = {**dbg, "route_text": r, "lens": spec["lens"], "lens_variant": spec["variant"]}
    return pack
