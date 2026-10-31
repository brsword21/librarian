"""KU lens B, round 3: b_r2 r2b packing (copied here unchanged, see lenses/ku/b_r2.py) + an OWN-VALUE constraint on
the pair (round-3 brief item 2).

Problem (test audit r2): 'How many cups of coffee do I drink each morning these days?' pairs "Carlos drinks three cups
of coffee every morning" (someone else's value) with the user's own update. r2c already labels such bare-name subject
sentences as someone else's (own = -1, b_semantic OWN_NAME), but the pair search still keeps them when every other
candidate is weak.
own_pair_fix: when a pair member's best sentence is someone else's value (own < 0), replace it by the best-scoring
session among the top `own_depth` sessions whose best sentence is the user's own (own > 0), carries a value of the
same type as the other pair member (b_r3_gate.typed_values), and is not an abandoned trial; chronology is re-derived.
If no such session exists the pair is kept (the hint still says to ignore other people's values).
"""
from __future__ import annotations

import math
import re

from lenses.ku import b_r2 as R2
from lenses.ku import b_semantic as B
from lenses.ku.b_r3_gate import REVERT, typed_values

try:
    from core.types import EvidencePack
except Exception:  # pragma: no cover
    EvidencePack = None

_R2B = dict(R2.VARIANTS["r2b"])
VARIANTS = {
    "r2b": dict(_R2B),                                          # control (= v1 ku route)
    "own": dict(_R2B, own_name=True, own_fix=True, own_depth=8),  # r2c ownership + own-value pair fix
    "bgm2": dict(_R2B, bg_miss=0.2, bigram_w_lo=0.3),
    "bgm3": dict(_R2B, bg_miss=0.3, bigram_w_lo=0.0),
    "bgm1": dict(_R2B, bg_miss=0.1, bigram_w_lo=0.3),
    "own6": dict(_R2B, own_name=True, own_fix=True, own_depth=6),
}


def own_pair_fix(r: dict, hx, question: str, p: dict) -> dict | None:
    pair, bbs, rank = list(r["pair"]), r["best_by_sess"], r["sess_rank"]
    # someone else's value = own < 0 AND no first-person word at all ('Carlos drinks three cups of coffee every
    # morning'); own < 0 alone is noisy on dev ("to my friend's birthday party", "He's actually ...", "getting used to")
    def _other(sid):
        return bbs[sid]["own"] < 0 and not B.FIRST_PERSON.search(bbs[sid]["raw"])
    if len(pair) < 2 or not any(_other(sid) for sid in pair):
        return None
    info = {"before": list(pair)}
    for i, sid in enumerate(list(pair)):
        if not _other(sid):
            continue
        mate = pair[1 - i]
        t_other = set(typed_values(bbs[mate]["raw"], question))
        cands = [c for c in rank[: p.get("own_depth", 8)] if c not in pair and bbs[c]["own"] > 0 and bbs[c]["val"]
                 and not bbs[c].get("asst") and not REVERT.search(bbs[c]["raw"])
                 and (not t_other or set(typed_values(bbs[c]["raw"], question)) & t_other)]
        if cands:
            pair[i] = cands[0]
    pair = sorted(dict.fromkeys(pair), key=lambda s: hx.sess_by_id[s]["sess_idx"])
    if pair == sorted(r["pair"], key=lambda s: hx.sess_by_id[s]["sess_idx"]):
        info["changed"] = False
        return info
    r["pair"] = pair
    r["sess_rank"] = pair + [s for s in rank if s not in pair]
    info["after"], info["changed"] = list(pair), True
    return info


def build(q, hx, **p):
    from core.pack import build_pack

    r = B.analyze(q, hx, **p)
    own_fix = own_pair_fix(r, hx, q.question, p) if p.get("own_fix") else None
    question = q.question
    pair, sess_rank, sents, best_by_sess = r["pair"], r["sess_rank"], r["sents"], r["best_by_sess"]

    extra = p.get("extra", 2)
    feats: dict = {}
    if p.get("gate"):
        ok, feats = R2.confidence(r, hx, question, p)
        if not ok:
            extra = p.get("extra_lo", 1)
        feats["confident"] = ok
    rest = [sid for sid in sess_rank if sid not in pair]
    keep = list(pair) + rest[:extra]

    unit_best: dict[int, float] = {}
    for s in sents:
        unit_best[s["uid"]] = max(unit_best.get(s["uid"], -1e9), s["score"])
    pinned, pack_uids = [], []
    for sid in keep:
        su = sorted({s["uid"] for s in sents if s["sid"] == sid and not s.get("asst")}, key=lambda uid: -unit_best[uid])
        n = p.get("units_per_sess", 2) if sid in pair else p.get("units_extra", 2)
        if sid in pair and su:
            pinned.append(su[0])           # the pair's best unit always enters first
        pack_uids.extend(su[:n])
        if best_by_sess[sid].get("asst"):
            (pinned if sid in pair else pack_uids).append(best_by_sess[sid]["uid"])

    # timeline hint: pair + shown sessions + (tl_extra) dropped context sessions, dated, oldest first
    tl_sids = list(keep) + [sid for sid in rest[extra: extra + p.get("tl_extra", 0)]]
    tl = []
    for sid in sorted(set(tl_sids), key=lambda x: hx.sess_by_id[x]["sess_idx"]):
        s = best_by_sess[sid]
        if p.get("tl_min_cov") is not None and not s.get("linked") and (
                s["cov"] < p["tl_min_cov"] or (s["raw"].rstrip().endswith("?") and not s["val"])):
            continue
        if sid in pair or (s["own"] > 0 and s["val"] and s["cov"] >= p.get("tl_cov", 0.6)):
            tl.append((hx.sess_by_id[sid]["date_str"], s["raw"]))

    ap = r["abstain_p"]
    miss_ph = []
    if p.get("bigram_w"):
        miss_ph = R2.missing_phrases(question, R2._user_text(hx))
        # r3 (brief item 3): the bigram signal counts only together with low attribute coverage (miss >= bg_miss),
        # so answerable phrase variants ('monthly rent', 'job title') are not pushed up
        w = p["bigram_w"] if r["miss"] >= p.get("bg_miss", 0.0) else p.get("bigram_w_lo", p["bigram_w"])
        z = math.log(ap / (1 - ap)) + w * min(2, len(miss_ph))
        ap = 1 / (1 + math.exp(-z))

    raw_absent = [w for w in re.findall(r"[A-Za-z][\w'-]+", question)[1:] if w[0].isupper() and B._stem(w) in r["absent"]]
    hint = B.build_hint(tl[:4], r["mode"], raw_absent if r["abstain_p"] > p.get("ab_hint", 0.6) else None) \
        if p.get("hint", True) else ""

    passages, included_turns, _chars = build_pack(q, hx, pack_uids, budget=p.get("budget", 6000),
                                                  window=p.get("window", 0), order="chrono", hint=hint,
                                                  max_sessions=len(keep), whole_turns=False, pinned=pinned)
    pack_ids = {ps.id for ps in passages if ps.id}
    cite = [sid for sid in pair if sid in pack_ids]
    return EvidencePack(question_id=q.question_id, variant=p.get("_variant", ""), route="ku", passages=passages,
                        hint=hint, cite_plan=cite or None, abstain_p=round(ap, 4),
                        included_turns=included_turns, computed=None,
                        debug={"ranking": r["ranked_units"], "pair": pair, "sess_rank": sess_rank[:8],
                               "mode": r["mode"], "qd": r["qd"], "miss": round(r["miss"], 3), "absent": r["absent"],
                               "gate": feats, "miss_ph": miss_ph, "n_pass": len(passages), "own_fix": own_fix})


