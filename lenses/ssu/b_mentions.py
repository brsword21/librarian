"""SSU lens B ("Semantyka"): a fact the USER stated about themself, once (or with later revisions).

Pipeline (see lenses/ssu/b_design.md):
  question -> head entity ("cat", "sourdough starter", "coffee shop"), question owner ("my" vs "my brother's"),
              recency cue ("end up", "the last X I mentioned", "now", "current"), declarative rewrites
  -> hybrid (BM25 + bge RRF) over USER units for the question and its declarative forms, fused by RRF
     + an anchor channel (user units containing the head noun), all reranked with the cross-encoder
  -> unit score = rerank logit + mention-act features: other-person subject/possessor, negated ("but I haven't"),
     tentative ("thinking of naming"), superseded ("old", "paperwork still says"), reply-to-assistant-question bonus
  -> session score = best unit + small bonus for a second hit (max-pooling: the fact is usually a side remark)
  -> pack: top sessions, the hit unit only (+ the assistant's preceding chunk when the hit is a short reply)
  -> cite_plan: top session; with a recency cue the LATEST clean candidate near the top score
  -> hint: own-statement rule (+ latest-wins when cued); abstain_p from the best clean logit and head-term coverage.

Pure-python helpers have a self-test: `.venv/bin/python -m lenses.ssu.b_mentions`.
Core imports are lazy so the helpers run without the model server.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict

from core.types import EvidencePack

_BASE = dict(pool=300, k_hybrid=100, w_bm25=1.0, w_dense=1.0, rrf_k=60, w_decl=0.7, rerank_depth=60, anchor_cap=40,
             pen_other=3.0, pen_neg=3.0, pen_tent=2.0, pen_old=2.0, bonus_reply=1.0, bonus_update=1.0,
             lam_second=0.15, drop=6.0, n_sess=4, budget=5000, window=0, prev_for_reply=True, next_for_cited=True, sweep_sess=3, units_cited=3,
             rec_delta=3.0, cite_margin=0.5, hint=True, tags=True, recency="cue",
             ab_bias=-1.0, ab_temp=2.0, ab_cov=0.35, ab_decoy=0.4)

VARIANTS = {
    # ranked by expected value on TEST (see b_design.md)
    "mention": dict(_BASE),                                               # B1: precise, tag-aware, recency on cue
    "mention_latest": {**_BASE, "recency": "always_value"},               # B3: latest-wins also without the cue
    "mention_wide": {**_BASE, "n_sess": 6, "budget": 8000, "window": 1},  # B2: recall-heavy pack, same ranking
    "plain": {**_BASE, "tags": False, "hint": False, "w_decl": 0.0, "anchor_cap": 0},  # control: hybrid+rerank only
}

# ----------------------------------------------------------------------------------------------------------------
# Question parsing (pure python)
# ----------------------------------------------------------------------------------------------------------------
STOP = set("""a an the of to in on at for with my me i we our you your is are was were be been do did does what which who
whom where when how many much that this those these it its by from about as or and before after have has had any some
i've i'm i'd me myself us up out over into than then there their they them can could would should will just so""".split())
SLOT = set("""name names named call called brand type kind sort breed color colour size model title value number speed
price cost amount percentage ratio time date day place location address favorite favourite usually currently current
now last first mention mentioned tell told end ended thing one new still really actually exactly""".split())
PERSON = ("friend|friends|wife|husband|partner|boyfriend|girlfriend|fianc[eé]e?|brother|sister|sibling|mom|mum|mother|"
          "dad|father|parents?|son|sons|daughter|daughters|kids?|child|children|toddler|baby|neighbou?r|coworker|"
          "co-worker|colleague|boss|manager|cousin|aunt|uncle|roommate|flatmate|niece|nephew|grandma|grandpa|"
          "grandmother|grandfather|grandson|granddaughter|classmate|teammate|nurse|doctor|teacher|tutor|client|"
          "student|member|someone|everyone|people|guy|woman|man|lady|in-laws?|family")

IRREG = {"buy": "bought", "go": "went", "take": "took", "get": "got", "meet": "met", "find": "found", "make": "made",
         "eat": "ate", "see": "saw", "give": "gave", "ride": "rode", "pay": "paid", "spend": "spent", "read": "read",
         "leave": "left", "catch": "caught", "teach": "taught", "keep": "kept", "have": "had", "do": "did",
         "begin": "began", "choose": "chose", "win": "won", "wear": "wore", "sell": "sold", "bring": "brought",
         "think": "thought", "put": "put", "set": "set", "run": "ran", "swim": "swam", "drink": "drank",
         "write": "wrote", "drive": "drove", "fly": "flew", "know": "knew", "grow": "grew", "throw": "threw",
         "lose": "lost", "send": "sent", "build": "built", "feel": "felt", "hear": "heard", "hold": "held",
         "sleep": "slept", "stand": "stood", "tell": "told", "say": "said", "become": "became", "come": "came",
         "beat": "beat", "cut": "cut", "split": "split", "sing": "sang", "steal": "stole", "break": "broke"}

_RECENCY = re.compile(r"\bend(?:ed)? up\b|\b(?:the )?(?:last|latest|most recent)\b(?! (?:week|weekend|month|year|"
                      r"time|night|day|summer|winter|spring|fall|autumn|monday|tuesday|wednesday|thursday|friday|"
                      r"saturday|sunday)\b)[\w\s'-]{0,40}\bI\b[\w\s'-]{0,20}\b(?:mention|told|said|talk)|"
                      r"\b(?:now|currently|current|these days|right now|at the moment|anymore|finally|settle[ds]? on)\b",
                      re.I)
_PAST_Q = re.compile(r"\b(previous|previously|before I|used to|former|formerly|my old|originally)\b", re.I)
SYN = {"dog": ["puppy", "pup"], "cat": ["kitten", "kitty"], "partner": ["husband", "wife", "boyfriend", "girlfriend"],
       "bicycle": ["bike"], "bike": ["bicycle"], "kid": ["child"], "child": ["kid"], "apartment": ["flat"],
       "flat": ["apartment"], "café": ["cafe", "coffee"], "cafe": ["café", "coffee"]}


def words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9'-]*", s.lower())


def stem(w: str) -> str:
    w = re.sub(r"'s$", "", w.lower())
    for suf in ("ings", "ing", "ies", "ied", "es", "ed", "s"):
        if len(w) - len(suf) >= 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def content_terms(q: str) -> list[str]:
    q = q.split("?")[0]
    return [w for w in words(q) if w not in STOP and w not in SLOT and len(w) > 2]


def past(v: str) -> str:
    v = v.lower()
    if v in IRREG:
        return IRREG[v]
    if v.endswith("e"):
        return v + "d"
    if re.search(r"[^aeiou]y$", v):
        return v[:-1] + "ied"
    return v + "ed"


def parse_question(text: str) -> dict:
    """-> {head, head_words, owner, recency, past_q, decl: [..], terms: [..]}. Pure regex, no models."""
    q = text.split("?")[0].strip()
    ql = q.lower()
    phrase = None
    pats = [
        r"\bmy ((?:[\w-]+ ){0,2}?[\w-]+?)'s name\b",                                # my (younger) son's name
        r"\bname of (?:my|the|that|our) ([\w' -]+?)(?= (?:i|where|that|who|which|for|at|in|from|you)\b|$)",
        r"\bnam(?:e|ed|ing) my ([\w' -]+?)$",                                       # end up naming my sourdough starter
        r"\bthe last ([\w -]+?) i (?:mentioned|told|said)",                          # the last state park I mentioned
        r"^(?:what|which) ([\w-]+(?: [\w-]+)?) (?:did|do|does|am|was|were|is|are|have|has) (?:i|my|you)\b",
        r"^(?:what|which) [\w-]+ (?:is|are|was|were) (?:the|my) ([\w -]+?)(?= (?:i|that|which|where|who)\b|$)",
        r"^how (?:many|much) ([\w-]+(?: [\w-]+)?) (?:do|did|does|have|has|am|was|were) (?:i|my)\b",
        r"\bmy ((?:[\w-]+ ){0,2}?[\w-]+)(?= (?:is|was|are|were|to|for|at|in|from|on|did|do|i)\b|$)",
    ]
    for p in pats:
        m = re.search(p, ql)
        if m:
            phrase = m.group(1).strip()
            break
    owner = "self"
    if phrase and "'s " in phrase:                      # "brother's new dog": the question is about someone else's
        owner = phrase.split("'s ")[0].split()[-1]
    hw = [w for w in words(phrase or "") if w not in STOP and w not in SLOT and not w.endswith("'s")]
    head = hw[-1] if hw else (content_terms(text)[-1] if content_terms(text) else "")
    return {"head": head, "head_words": hw, "owner": owner, "phrase": phrase or "",
            "recency": bool(_RECENCY.search(text)), "past_q": bool(_PAST_Q.search(q)),
            "decl": declaratives(text), "terms": content_terms(text)}


def declaratives(text: str) -> list[str]:
    """LLM-free question -> statement rewrites, the way a user would have said it (first person)."""
    q = re.sub(r"\s+(?:now|currently|these days|right now|at the moment)$", "", text.split("?")[0].strip(), flags=re.I)
    ql = q[0].lower() + q[1:] if q else q
    out = []
    m = re.match(r"(?:what(?:'s| is| was)) (?:the name of )?my ([\w' -]+?)(?:'s name)?$", ql, re.I)
    if m and ("name" in ql):
        x = m.group(1)
        out += [f"my {x} is named", f"my {x}, her name is, his name is, called"]
    m = re.match(r"what did i (?:end up |finally )?nam(?:e|ing) (my [\w' -]+)$", ql, re.I)
    if m:
        out += [f"I named {m.group(1)}", f"I renamed {m.group(1)}, it is called"]
    m = re.match(r"(?:what|which) (?:was|is) the name of (?:the|that|my) ([\w' -]+)$", ql, re.I)
    if m and not out:
        out += [f"the {m.group(1)} is called", m.group(1)]
    m = re.match(r"(?:what|which) was the (?:last|latest) ([\w -]+?) i (?:mentioned|told you about)( [\w -]+)?$", ql, re.I)
    if m and not out:
        rest = re.sub(r"^i(?:'d| was| am| had| have)? ", "", (m.group(2) or "").strip(), flags=re.I)
        g = re.match(r"([a-z]+?)ing\b(.*)$", rest)
        if g:
            base = g.group(1) if g.group(1) + "e" not in IRREG else g.group(1) + "e"
            rest = past(base) + g.group(2)
        out += [f"I {rest} the {m.group(1)}".replace("  ", " ").strip(), f"the {m.group(1)} I {rest}".strip()]
    if not out:
        m = re.match(r"(what|which|where|who|when|how \w+)( [\w-]+)? (did|do|does|am|is|are|was|were|have|has) "
                     r"(i|my) ([\w-]+)(.*)$", ql, re.I)
        if m:
            wh, noun, aux, subj, v, rest = m.groups()
            noun = (noun or "").strip()
            if subj.lower() == "i":
                verb = past(v) if aux.lower() in ("did",) else v
                if aux.lower() in ("am", "was"):
                    verb = f"{'am' if aux.lower() == 'am' else 'was'} {v}"
                s = f"I {verb}{rest}"
                out.append(f"the {noun} {s}" if noun and wh.lower() in ("what", "which") else s)
            else:  # "What breed is my dog" -> "my dog is a breed"
                out.append(f"my {v}{rest} {aux} {noun}".strip())
    return [re.sub(r"\s+", " ", o).strip() for o in out if o.strip()][:2]


# ----------------------------------------------------------------------------------------------------------------
# Mention-act tagging (pure python): is this sentence the user's OWN, factual, current statement about the head?
# ----------------------------------------------------------------------------------------------------------------
_SENT = re.compile(r"(?<!\bMr\.)(?<!\bDr\.)(?<!\bSt\.)(?<!\bMs\.)(?<!\bMt\.)(?<!Mrs\.)(?<!\bvs\.)(?<!\bJr\.)"
                   r"(?<!Bros\.)(?<!\bCo\.)(?<=[.!?])\s+|\s+[—–]{1,2}\s*|[—–](?=[A-Z])|\n+")
_LEAD = r"^(?:(?:oh|also|and|but|so|anyway|plus|well|ha|by the way|on a [\w ]+? note|funny enough|speaking of [\w ]+?)[,\s]+)*"


def _sentences_with(text: str, stems: list[str]) -> list[str]:
    out = []
    for s in _SENT.split(text):
        sl = s.lower()
        if any(re.search(r"\b" + re.escape(st), sl) for st in stems):
            out.append(s.strip())
    return out


def tag_mention(text: str, ctx: str, pq: dict) -> set[str]:
    """Tags for a user unit relative to the parsed question: other / negated / tentative / old / update / reply."""
    tags: set[str] = set()
    head = pq["head"]
    qwords = set(pq["terms"]) | set(pq["head_words"]) | {pq["owner"]}
    if ctx and ctx.rstrip().endswith("?"):
        first = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]
        if len(first) <= 60:
            tags.add("reply")
            if re.search(r"\b(name|call|which|what)\b", ctx, re.I):
                tags.add("reply_named")
    if not head:
        return tags
    st = stem(head)[: max(4, len(stem(head)))]
    stems = [st] + [stem(x) for x in SYN.get(head, [])]
    qwords = qwords | set(SYN.get(head, []))
    sents = _sentences_with(text, stems) or []
    person = r"(?:" + PERSON + r")"
    for s in sents:
        sl = s.lower()
        pos = max(sl.find(x) for x in stems)
        pre = sl[max(0, pos - 40): pos]
        if pq["owner"] == "self":
            m = re.search(_LEAD + r"(?:my|our|a|an|one of my|another|this|the) (?:[\w-]+ ){0,2}?(" + person + r")\b", sl)
            if m and m.group(1) not in qwords and not re.match(_LEAD + r"(?:i|we)\b", sl):
                tags.add("other")
            if re.search(_LEAD + r"[a-z]+ (?:just )?(?:said|says|told|thinks|swears|recommended|mentioned|tried|"
                         r"adopted|named|ran|bought|got)\b", sl) and re.match(_LEAD + r"[A-Z]", s) \
                    and not re.match(_LEAD + r"(?:i|we|my|our|it|this|that|the)\b", sl):
                tags.add("other")
            if re.search(r"\b(?:his|her|their|" + person + r"'s|[a-z]+'s) (?:[\w-]+ ){0,2}$", pre) and \
                    not re.search(r"\b(?:" + "|".join(map(re.escape, qwords - {""})) + r")'s (?:[\w-]+ ){0,2}$", pre):
                tags.add("other")
            if re.search(r"\b(?:a|an) (?:[\w-]+ ){0,2}(?:" + "|".join(map(re.escape, stems)) + r")\w* (?:named|called)\b",
                         sl) and not re.match(_LEAD + r"(?:i|we|i've|we've|i'm)\b", sl):
                tags.add("other")
            if re.search(r"\b(?:saw|read about|heard about|came across|on a forum|online|in a video|on tv)\b", sl):
                tags.add("other")
        if re.search(r"\bbut (?:i|we)\b[^.]{0,30}\b(?:haven't|hasn't|didn't|did not|have not|never|not)\b", sl) or \
                re.search(r"\b(?:i|we) (?:still )?(?:haven't|didn't|never|did not|have not) (?:\w+ ){0,2}?(?:tried|been|"
                          r"joined|gone|visited|bought|camped|used|named|signed|booked|eaten|made|done|read|finished)\b",
                          sl) or re.search(r"\bnot (?:yet|actually)\b|\binstead of\b|\brather than\b", sl):
            tags.add("negated")
        if re.search(r"\b(?:thinking (?:of|about)|considering|considered|might|maybe|plan(?:ning)? to|want(?:ed)? to|"
                     r"hoping to|would like to|toying with|was going to|could)\b", pre):
            tags.add("tentative")
        if re.search(r"\b(?:old|former|previous|ex-|used to|still says|originally|at first|no longer|anymore)\b", sl):
            tags.add("old")
        if re.search(r"\b(?:renamed|switched to|changed (?:it )?to|now|finally|settled on|ended up|went with|"
                     r"decided on|these days)\b", sl):
            tags.add("update")
    if "reply_named" in tags:
        tags.discard("other")
    return tags


def adjust(score: float, tags: set[str], pq: dict, p: dict) -> float:
    if not p.get("tags", True):
        return score
    s = score
    if "other" in tags and not ("reply_named" in tags):
        s -= p["pen_other"]
    if "negated" in tags:
        s -= p["pen_neg"]
    if "tentative" in tags and "update" not in tags:
        s -= p["pen_tent"]
    if "old" in tags:
        s += p["pen_old"] * 0.5 if pq["past_q"] else -p["pen_old"] * (1.0 if pq["recency"] else 0.5)
    if "reply_named" in tags or ("reply" in tags and pq["head"]):
        s += p["bonus_reply"]
    if "update" in tags and pq["recency"]:
        s += p["bonus_update"]
    return s


DECOY = {"other", "negated", "tentative"}


def build_hint(pq: dict, p: dict, abstain_p: float) -> str:
    if not p.get("hint", True):
        return ""
    h = ("Answer from the user's own first-person statements about themself. Statements about other people "
         "(friend, partner, coworker), plans or options not taken, and things the user did not do do not count.")
    if pq["recency"]:
        h += " If the user gave different values at different times, the most recent dated statement wins."
    elif pq["past_q"]:
        h += " The question asks for the earlier value, not the current one."
    if abstain_p >= 0.7:
        h += " If no excerpt states it for the user themself, reply INSUFFICIENT_EVIDENCE."
    return h


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))


# ----------------------------------------------------------------------------------------------------------------
# Lens
# ----------------------------------------------------------------------------------------------------------------
_IDF_CACHE: dict[tuple, dict] = {}


def _df(hx) -> dict[str, int]:
    key = (getattr(hx, "split", ""), getattr(hx, "history_id", id(hx)))
    if key not in _IDF_CACHE:
        df: dict[str, int] = defaultdict(int)
        for u in hx.units:
            if u.role == "user":
                for w in set(stem(w) for w in words(u.index_text)):
                    df[w] += 1
        _IDF_CACHE.clear()
        _IDF_CACHE[key] = df
    return _IDF_CACHE[key]


def build(q, hx, **params) -> EvidencePack:
    from core.pack import build_pack

    p = {**_BASE, **params}
    pq = parse_question(q.question)
    if p["recency"] == "always_value" and re.search(r"\b(name|brand|which|what)\b", q.question, re.I):
        pq["recency"] = True
    queries = [q.question.split("?")[0] + "?"] + ([d for d in pq["decl"]] if p["w_decl"] else [])

    # 1. candidate pool: RRF over the question and its declarative rewrites, user units only
    fused: dict[int, float] = defaultdict(float)
    for qi, qq in enumerate(queries):
        w = 1.0 if qi == 0 else p["w_decl"]
        for r, (uid, _s) in enumerate(hx.hybrid(qq, k=p["k_hybrid"], roles=["user"], w_bm25=p["w_bm25"],
                                                w_dense=p["w_dense"], rrf_k=p["rrf_k"], pool=p["pool"])):
            fused[uid] += w / (p["rrf_k"] + r + 1)
    pool = sorted(fused, key=lambda u: -fused[u])[: p["rerank_depth"]]
    # anchor channel: user units that literally contain the head noun (recall for "the cat" x 40 sessions)
    if p["anchor_cap"] and pq["head"]:
        st = stem(pq["head"])
        rx = re.compile(r"\b" + re.escape(st[: max(4, len(st))]), re.I)
        terms = [stem(t) for t in pq["terms"]]
        extra = []
        for u in hx.units:
            if u.role == "user" and u.uid not in fused and rx.search(u.text):
                lt = u.index_text.lower()
                extra.append((sum(1 for t in terms if t and t in lt), -u.uid, u.uid))
        extra.sort(reverse=True)
        pool += [x[2] for x in extra[: p["anchor_cap"]]]

    # 2. rerank with the original question, 3. mention-act adjustments
    rr = hx.rerank(q.question, pool) if pool else []
    # session sweep: rerank every user unit of the top sessions (the answer is often a short reply that lexical and
    # dense pools miss while a sibling turn of the same session ranks high)
    if p["sweep_sess"] and rr:
        top_sids = list(dict.fromkeys(hx.units[u].session_id for u, _ in rr))[: p["sweep_sess"]]
        seen = {u for u, _ in rr}
        more = [u.uid for u in hx.units if u.session_id in top_sids and u.role == "user" and u.uid not in seen]
        if more:
            rr = sorted(rr + hx.rerank(q.question, more), key=lambda x: -x[1])
    scored, tags_of = [], {}
    for uid, s in rr:
        u = hx.units[uid]
        tg = tag_mention(u.text, u.ctx, pq)
        tags_of[uid] = tg
        scored.append((uid, s, adjust(s, tg, pq, p)))
    scored.sort(key=lambda x: -x[2])

    # 4. session aggregation (max-pooling + small second-hit bonus)
    by_sess: dict[str, list] = defaultdict(list)
    for uid, s, a in scored:
        by_sess[hx.units[uid].session_id].append((a, uid, s))
    sess_rank = []
    for sid, hits in by_sess.items():
        hits.sort(reverse=True)
        bonus = p["lam_second"] * max(0.0, hits[1][0]) if len(hits) > 1 else 0.0
        sess_rank.append((hits[0][0] + bonus, sid, hits))
    sess_rank.sort(key=lambda x: -x[0])
    top = sess_rank[0][0] if sess_rank else -20.0
    chosen = [x for x in sess_rank if x[0] >= top - p["drop"]][: p["n_sess"]] or sess_rank[:1]

    # 5. cite plan: top session, or the latest clean candidate near the top when the question is about recency
    cite = [chosen[0][1]] if chosen else []
    if chosen and pq["recency"]:
        near = [x for x in chosen if x[0] >= top - p["rec_delta"] and not (tags_of[x[2][0][1]] & DECOY)]
        if near:
            latest = max(near, key=lambda x: hx.sess_by_id[x[1]]["sess_idx"])
            cite = [latest[1]]
    elif len(chosen) > 1 and chosen[0][0] - chosen[1][0] < p["cite_margin"]:
        cite.append(chosen[1][1])

    # 6. abstention: best clean logit + head-term coverage in the top units
    clean = [a for uid, s, a in scored if not (tags_of[uid] & DECOY)]
    best_clean = clean[0] if clean else (scored[0][2] - 3.0 if scored else -20.0)
    p_ans = _sigmoid((best_clean - p["ab_bias"]) / p["ab_temp"])
    pen = 0.0
    df = _df(hx)
    key_terms = sorted({stem(t) for t in pq["terms"] if stem(t) in df}, key=lambda t: df[t])[:1]
    top_text = " ".join(hx.units[uid].index_text.lower() for uid, _, _ in scored[:3])
    if key_terms and not any(re.search(r"\b" + re.escape(t[: max(4, len(t))]), top_text) for t in key_terms):
        pen += p["ab_cov"]
    head_hits = [uid for uid, _, a in scored[:10] if pq["head"] and stem(pq["head"])[:4] in hx.units[uid].text.lower()
                 and a >= top - p["drop"]]
    if head_hits and all(tags_of[u] & DECOY for u in head_hits):
        pen += p["ab_decoy"]
    abstain_p = max(0.0, min(1.0, 1.0 - p_ans * (1.0 - min(pen, 0.9))))

    # 7. pack: hit units (best 1-2 per chosen session) + preceding assistant chunk for short replies
    ranked = []
    for _sc, sid, hits in chosen:
        for a, uid, _s in hits[: (p["units_cited"] if sid in cite else 2)]:
            if a < hits[0][0] - (8.0 if sid in cite else 2.0) and uid != hits[0][1]:
                continue
            ranked.append(uid)
            if p["prev_for_reply"] and "reply" in tags_of[uid]:
                ranked += [j for j in hx.neighbors(uid, 1, 0) if j != uid]
            if p["next_for_cited"] and sid in cite and uid == hits[0][1]:   # assistant's restatement (gold turn 3%)
                ranked += [j for j in hx.neighbors(uid, 0, 1) if j != uid]
    hint = build_hint(pq, p, abstain_p)
    passages, included, chars = build_pack(q, hx, ranked, budget=p["budget"], window=p["window"], order="chrono",
                                           hint=hint, max_sessions=p["n_sess"])
    in_pack = {ps.id for ps in passages}
    cite = [c for c in cite if c in in_pack] or ([passages[0].id] if passages else [])
    return EvidencePack(question_id=q.question_id, variant=params.get("_variant", ""), route="ssu",
                        passages=passages, hint=hint, cite_plan=cite, abstain_p=abstain_p,
                        included_turns=included, computed=None,
                        debug={"ranking": [uid for uid, _, _ in scored] + [u for u in fused if u not in tags_of],
                               "pq": {k: v for k, v in pq.items()}, "top": top, "best_clean": best_clean,
                               "tags": {str(u): sorted(t) for u, t in list(tags_of.items())[:15] if t},
                               "sessions": [(round(x[0], 2), x[1]) for x in chosen]})


# ----------------------------------------------------------------------------------------------------------------
# Self-test (pure python; no models): `.venv/bin/python -m lenses.ssu.b_mentions`
# ----------------------------------------------------------------------------------------------------------------
def _selftest() -> None:
    import json
    from pathlib import Path

    rows = [json.loads(line) for line in open(Path(__file__).resolve().parents[2] / "runs/samples/ssu.jsonl")]
    print("== question parsing ==")
    extra = ["What did I end up naming my sourdough starter?", "What was the last restaurant I mentioned trying?",
             "What is my younger son's name?", "What is the name of my brother's new dog?",
             "What was the last state park I mentioned camping at?", "What did I name my new podcast?",
             "What was my previous occupation?", "What brand is the bicycle I ride to work?"]
    for t in [r["question"] for r in rows] + extra:
        pq = parse_question(t)
        print(f"{t[:62]:62s} head={pq['head']!r:16s} owner={pq['owner']:8s} rec={int(pq['recency'])} "
              f"past={int(pq['past_q'])} decl={pq['decl']}")
    print("\n== mention tags (test-style decoys and dev gold turns) ==")
    cases = [
        ("What is my dog's name?", "Good tip. On a happier note, My friend Helen just adopted a cavoodle puppy named Luna.", "", {"other"}),
        ("What is my dog's name?", "The hospital's children's ward has a therapy dog named Archie who visits on Fridays.", "", {"other"}),
        ("What was the last restaurant I mentioned trying?", "Oh, and My wife tried a new wood-fired pizza restaurant in Decatur last weekend and said it was fantastic.", "", {"other"}),
        ("What was the last restaurant I mentioned trying?", "Also, My brother said Fox Bros. Bar-B-Q is the best barbecue restaurant in Atlanta, but I haven't tried it yet.", "", {"other", "negated"}),
        ("What was the last state park I mentioned camping at?", "My son's baseball team had a picnic at Red Top Mountain State Park, but we didn't camp overnight.", "", {"negated"}),
        ("What was the last state park I mentioned camping at?", "We camped at Cloudland Canyon State Park last weekend, and the views were incredible.", "", set()),
        ("What did I end up naming my sourdough starter?", "I'm thinking of naming my sourdough starter Bubbles. I blame the algorithm.", "", {"tentative"}),
        ("What did I end up naming my sourdough starter?", "Ha, no way. My friend Valentina named her sourdough starter Bubbles too.", "", {"other"}),
        ("What did I end up naming my sourdough starter?", "I saw a sourdough starter named Herman in a French baking forum.", "", {"other"}),
        ("What did I end up naming my sourdough starter?", "I've renamed my sourdough starter Masa, after masa madre.", "", {"update"}),
        ("What is my cat's name?", "Bica. Like the Lisbon espresso, because she's small, dark, and keeps me up. My son claims she's his cat.", "What's her name?", {"reply", "reply_named"}),
        ("What is my cat's name?", "By the way, I finally got my cat microchipped, and the paperwork still says Luna.", "", {"old"}),
        ("What's the name of my running group?", "A nurse at work invited me to a hospital running group called Stumptown Joggers, but I didn't join.", "", {"other", "negated"}),
        ("What is my younger son's name?", "It's funny how time goes—My younger son Daniel is moving to Brisbane for work.", "", set()),
        ("What breed is my dog?", "I'm thinking of getting Max a new collar. Any brand that would suit a Golden Retriever like Max?", "", set()),
        ("Where did I redeem a $5 coupon on coffee creamer?", "I actually redeemed a $5 coupon on coffee creamer last Sunday, since I didn't know I had it in my email inbox.", "", set()),
    ]
    ok = 0
    for qt, txt, ctx, want in cases:
        got = tag_mention(txt, ctx, parse_question(qt))
        core_got = got & {"other", "negated", "tentative", "old", "update", "reply", "reply_named"}
        good = want <= core_got and (bool(want & DECOY) == bool(core_got & DECOY))
        ok += good
        print(f"{'OK ' if good else 'BAD'} {sorted(core_got)!s:32s} want⊇{sorted(want)!s:24s} {txt[:70]}")
    print(f"tag cases ok: {ok}/{len(cases)}")
    gold_decoy = 0
    n = 0
    for r in rows:
        if r["split"] != "dev" or r["abstain"]:
            continue
        pq = parse_question(r["question"])
        for t in r["gold_turns"]:
            if t["role"] == "user":
                n += 1
                ctx = t["prev_turn_tail"].strip().split("\n")[-1][-220:]
                tg = tag_mention(t["text"], ctx, pq)
                if tg & DECOY:
                    gold_decoy += 1
                    print(f"  dev gold tagged as decoy: {sorted(tg)} | {r['question']} | {t['text'][:120]}")
    print(f"dev gold user turns tagged as decoy: {gold_decoy}/{n}")
    print("\n== hints ==")
    for t in ["What is my cat's name?", "What did I end up naming my sourdough starter?", "What was my previous occupation?"]:
        print(f"{t}: {build_hint(parse_question(t), _BASE, 0.2)}")


if __name__ == "__main__":
    _selftest()
