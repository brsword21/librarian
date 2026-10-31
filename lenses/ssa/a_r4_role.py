"""SSA-A round 4: role detector r4 = a_r3_role (frozen, v2) + an impersonal-question rule on sentence evidence.

Why: on dev, 7 gold-ssa questions still sit on the ssu route. The ssu lens appends "Answer from what the user said
about their own X" to them, and real Reactor abstained on a pack like that in the calibration (Patagonia).
Five of the seven have no first-person word (nf0) and a negative unit-level CE margin d (assistant - user), so neither
p_b nor p_fit reaches 0.8:
  Rome restaurant (d -3.08), powwows (-1.00), President's advisor (-4.99, PA 0 on the ssu lens), Bajimaya (-3.57),
  Andy's scene script (-8.18).
They cannot be separated from the nf0 ssu / ku questions in the same d band with d alone ("How long did it take to
move to the new apartment?" d -1.04, "How long did Alex marinate the BBQ ribs?" -4.95, "Where did Rachel move?" -6.19).

New evidence (sentence level, lenses/ssa/scratch_a/r4/sent_feats.py):
  u_first = first-person words in the best user SENTENCE (CE over the sentences of the top-5 user units).
            The nf0 questions about the user's life still match a first-person user statement ("it took me and my
            friends around 5 hours to move", "I remember Alex t...", "my friend Rachel who recently moved", uf >= 1).
            The nf0 ssa questions match user text with no first-person word: a pasted article or case ("Arati
            Prabhakar, the President's Chief Advisor ..."), a pasted script line, a request ("Can you recommend some
            authentic Italian restaurants in Rome?") -> uf = 0.
  d_sent  = best assistant sentence CE - best user sentence CE. A unit-level margin can be negative because a long
            user unit carries many query terms while the assistant's answer sentence still wins at sentence level
            (powwows: d -1.00, d_sent +6.38).
Rule: nf0 and p_r3 < 0.8 and (u_first == 0 or d_sent >= 3) -> p = 0.85.
  0.85 passes the ssu threshold (0.8) and never the multi one (0.9), so only the ssu route changes.
  dev: 5 of 5 nf0 ssu-routed gold-ssa questions below 0.8 fire; 0 of the 3 nf0 ssu/ku negatives (uf 2 / 4 / 2,
  d_sent -3.57 / -2.58 / -5.86). dev200: 0 firings (the only nf0 ssu question below 0.8 is the apartment one).
  test: 0 firings by construction - every ssu- and multi-routed test question has a first-person word (nf0 = 0),
  so no test pack can change.
Role-play rule (first-person questions, rp=True): u_first == 0 and d >= 2 and d_sent >= 3 -> p = 0.85.
  dev: fires on the two "designation on my jumpsuit" role-play questions (gold ssa, the user talks to a character:
  "Wasn't there a designation for your study on your jumpsuit?") and on 3 "should I" questions the advice rule
  already hands off; 0 non-ssa. dev200: 0. test: 0 (nearest: "the museum where I work", u_first 0 but d -0.70).
lenses/ssa/a_r4_role_nf0.py = the nf0 rule alone (rp=False).
Drop-in role_module for lenses/ssu/a_r3_route.py (and merged_r2 wrappers).
Measured (tag r4-ssa-a, lens lenses/ssa/a_r4_routed.py = pipeline v2 with this module on the ssu route only):
  gold ssa routed dev 93.0 -> 93.6 (PA 0.991 -> 1.000, Sall 92.8 -> 93.3); dev200 93.7 = 93.7.
  ssu-routed slice dev 88.8 -> 89.3 (Sall 89.3 -> 89.8, gold ssa on the ssa route 43 -> 50 of 50, ssu/ku/multi/
  temporal rows identical = FP 0); dev200 88.8 = 88.8. Full routed dev200 87.0 = 87.0 (Sall 85.2 = 85.2).
  Test: harness.audit --compare runs/final/v2_test_packs.jsonl -> 0 of 45 ssu packs change. NOT for the final pass.
"""
from __future__ import annotations

import re

from harness.sweep import load_lens

_loaded: dict = {}


def _lens(path: str):
    if path not in _loaded:
        _loaded[path] = load_lens(path)
    return _loaded[path]


_FIRST_Q = re.compile(r"\b(I|my|me|mine|I'm|I've|I'd|I'll|myself|our|ours|us)\b", re.I)
_FIRST_S = re.compile(r"\b(I|my|me|mine|I'm|I've|I'd|I'll|myself|our|ours|us|we|we're|we've)\b", re.I)
_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def _sents(t: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(t) if len(s.strip()) > 15]


def sent_features(q, hx, n: int = 40, per_role: int = 5) -> dict:
    """Best user / assistant sentence by cross-encoder over the sentences of the top `per_role` units per role
    (units from the same CE-reranked top-n hybrid pool as b_role.role_features, so the unit rerank is cached)."""
    cand = hx.hybrid(q.question, k=100, pool=300)
    rr = sorted(hx.rerank(q.question, [u for u, _ in cand[:n]]), key=lambda x: -x[1])
    top = {"user": [], "assistant": []}
    for u, _s in rr:
        r = hx.units[u].role
        if r in top and len(top[r]) < per_role:
            top[r].append(u)
    out = {}
    for role, uids in top.items():
        ss = [s for u in uids for s in _sents(hx.units[u].text)]
        if not ss:
            out[role] = (-20.0, "")
            continue
        sc = hx.rerank_texts(q.question, ss)
        i = max(range(len(ss)), key=lambda j: sc[j])
        out[role] = (float(sc[i]), ss[i])
    return {"cs_a": out["assistant"][0], "cs_u": out["user"][0],
            "d_sent": out["assistant"][0] - out["user"][0],
            "u_first": len(_FIRST_S.findall(out["user"][1])), "u_sent": out["user"][1][:200]}


def role_guess(q, hx, thr: float = 0.8, ds_min: float = 3.0, p_fire: float = 0.85, rp: bool = True,
               rp_d: float = 2.0) -> float:
    """nf0 rule (impersonal question) and, with rp, the first-person 'role-play' rule (see module docstring)."""
    p = _lens("lenses/ssa/a_r3_role.py").role_guess(q, hx)
    if p >= thr:
        return p
    first = bool(_FIRST_Q.search(q.question))
    if first and not rp:
        return p
    if first:
        # first-person question whose best user sentence states nothing in the first person while the assistant
        # leads on both the unit and the sentence margin: the user is role-playing / quoting, the assistant
        # narrated the fact ("What designation on my jumpsuit led me to the file number ...?")
        d = _lens("lenses/ssa/b_role.py").role_features(q, hx)["d"]
        if d < rp_d:
            return p
        f = sent_features(q, hx)
        return max(p, p_fire) if f["u_first"] == 0 and f["d_sent"] >= ds_min else p
    f = sent_features(q, hx)
    if f["u_first"] == 0 or f["d_sent"] >= ds_min:
        return max(p, p_fire)
    return p
