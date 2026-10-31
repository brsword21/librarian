"""SSA lens B, round 4: in-session quote fallback on top of the frozen v2 ssa lens (a_recsent r2_conf2).

v2 quotes the recommendation line only when its structural score beats every OTHER session's best sentence by 1.3x.
The pack holds one session, so a decoy in another session (Coach Elena for "strength" vs Coach Miriam for
"speedwork") blocks the quote although Reactor never sees the decoy. Category words can also be missing from the line
("Heden in Baixa has a good day pass" for a coworking space), which makes the cross-encoder useless there (-11.4).

Fallback (brief item 1, adapted): when v2 emits no quote on a "you recommended" question, look at the assistant
sentences of the cited session that are in the pack. Quote the best one when it is clearly the session's own answer:
  - it carries a name/value (has_entity), a recommendation cue (cue > 0), no third-party / past / contrast flag,
  - it has a positive structural score (kind / purpose / question-term overlap),
  - and it is unique: no other in-pack candidate has a positive structural score, or (variant semq_ce) its
    cross-encoder logit against the question beats the runner-up by >= ce_margin.
Passages, cite_plan and abstain_p are unchanged; only the hint grows by one line (chars +~150).
Imports the frozen lens; edits nothing.
"""
import re

from core.types import EvidencePack
from lenses.ssa import a_recsent as A

_INNER = "r2_conf2"
VARIANTS = {
    "v2": {"fb": None},                                     # control: frozen v2 ssa lens
    "semq": {"fb": "unique"},                               # unique structural candidate in the cited session
    "semq_ce": {"fb": "ce", "ce_margin": 3.0},              # unique OR clear CE margin over the in-pack runner-up
    # strict: candidates must have v2's full recommendation shape (rec_shape == 1: cue + name + kind/purpose fit +
    # overlap >= 0.5) -- dev showed the loose candidate set quotes list chatter in long sessions (0/5 correct)
    "semq_shape": {"fb": "unique", "min_shape": 1.0},
}
_QUOTE = "Likely the line you need"


def _candidates(q, hx, pk, qp, idf, min_shape=0.0):
    sid = pk.cite_plan[0] if pk.cite_plan else None
    if sid is None:
        return []
    inc = set(pk.included_turns or [])
    out = []
    for t in hx.sess_by_id[sid]["turns"]:
        if t["role"] != "assistant" or (inc and t["turn_id"] not in inc):
            continue
        for s in A.sentences(t["content"]):
            sc, f = A.sent_struct(s, qp, idf)
            if sc > 0 and f.get("ent") and f.get("cue") and not (f.get("third") or f.get("past") or f.get("contra")):
                if A.rec_shape(f, qp) >= min_shape:
                    out.append((s, sc, f))
    return out


def build(q, hx, **params) -> EvidencePack:
    inner = dict(A.VARIANTS[_INNER])
    inner["_variant"] = params.get("_variant", "")
    pk = A.build(q, hx, **inner)
    fb = params.get("fb")
    dbg = pk.debug or {}
    qp_d = dbg.get("qp", {})
    if not fb or not qp_d.get("rec_style") or _QUOTE in (pk.hint or "") or not pk.passages:
        return pk
    qp = A.parse_question(q.question)
    qp["cue_floor"] = inner.get("cue_floor", 0.4)
    cands = _candidates(q, hx, pk, qp, A.history_idf(hx), params.get("min_shape", 0.0))
    if not cands:
        dbg["fb"] = "none"
        return pk
    cands.sort(key=lambda c: -c[1])
    pick = None
    if len(cands) == 1:
        pick = cands[0]
    elif fb == "ce":
        ce = hx.rerank_texts(q.question, [c[0] for c in cands])
        order = sorted(range(len(cands)), key=lambda i: -ce[i])
        if ce[order[0]] - ce[order[1]] >= params.get("ce_margin", 3.0):
            pick = cands[order[0]]
    if pick is None:
        dbg["fb"] = f"ambiguous:{len(cands)}"
        return pk
    sent = re.sub(r"[*_`#]+", "", pick[0]).strip()
    sid = pk.cite_plan[0]
    date = hx.sess_by_id[sid]["date_str"]
    hint = (pk.hint + " " if pk.hint else "") + f"{_QUOTE} (assistant, session of {date}): \"{sent[:260]}\""
    dbg["fb"] = "quote"
    dbg["fb_sentence"] = sent
    return EvidencePack(question_id=pk.question_id, variant=params.get("_variant", ""), route=pk.route,
                        passages=pk.passages, hint=hint, cite_plan=pk.cite_plan, abstain_p=pk.abstain_p,
                        included_turns=pk.included_turns, computed=pk.computed, debug=dbg)
