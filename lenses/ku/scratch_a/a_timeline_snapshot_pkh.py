"""KU lens A ("Struktura"): attribute timeline.

Idea: a knowledge-update question asks for the latest (or the previous) value of one attribute of the user.
1. Parse the question: attribute key terms (+ rule-based synonyms), answer type (number / time / day / name / place /
   frequency / duration / yes-no), direction (latest / previous / both / compare).
2. Retrieve candidate units (BM25 on cleaned + synonym-expanded query, optionally fused with dense, optionally reranked).
   Assistant units are kept too: in the test set updates are sometimes only restated by the assistant
   ("You mentioned your long run has shifted to Sundays at 6:30 a.m.").
3. Sentence-level mention extraction: IDF-weighted coverage of the key terms, a value of the answer type, ownership
   (the user's own attribute vs a friend's / sister's / coworker's), change cues ("now", "switched", "renamed") and old
   cues ("used to", "old", "previous").
4. Timeline: the user's own mentions sorted by date. Newest strong mention = N, the latest earlier mention with a
   different value = O. Cite exactly [O, N] (gold KU evidence is always 2 sessions).
5. Pack: mention units of N and O first, then the other mentions, then the rest of the ranking; chrono order, small
   budget. Hint = direction rule + (optionally) a dated quote timeline + ownership warning + absent-term note.

Pure-python helpers (question parsing, value grammar, ownership, timeline) have a self-test:
    .venv/bin/python -m lenses.ku.a_timeline            # parses samples, runs the timeline on gold turns
    .venv/bin/python -m lenses.ku.a_timeline --bm25 dev # BM25-only session-pair check on dev KU (no model server)
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from core.types import EvidencePack

try:  # same stemmer as core.index (bm25s + PyStemmer)
    import Stemmer

    _ST = Stemmer.Stemmer("english")

    def _stem(words: list[str]) -> list[str]:
        return _ST.stemWords(words)
except Exception:  # pragma: no cover
    def _stem(words: list[str]) -> list[str]:
        return [w[:-1] if w.endswith("s") else w for w in words]


VARIANTS = {
    # ranked by expected value on TEST (see a_design.md)
    "tl_rerank": {"retr": "rerank", "expand": True, "hint": "timeline", "cite": "pair", "budget": 6000,
                  "max_sessions": 5, "window": 1, "pool": 200, "rerank_k": 40},
    "tl_hybrid": {"retr": "hybrid", "expand": True, "hint": "timeline", "cite": "pair", "budget": 6000,
                  "max_sessions": 5, "window": 1, "pool": 200},
    "tl_bm25": {"retr": "bm25", "expand": True, "hint": "timeline", "cite": "pair", "budget": 6000,
                "max_sessions": 5, "window": 1, "pool": 200},
    "rule_top2": {"retr": "hybrid", "expand": False, "hint": "rule", "cite": "top2", "budget": 6000,
                  "max_sessions": 4, "window": 1, "pool": 200},
    "tl_wide": {"retr": "rerank", "expand": True, "hint": "timeline", "cite": "pair", "budget": 9000,
                "max_sessions": 8, "window": 1, "pool": 300, "rerank_k": 60},
    "tl_rerank_strong": {"retr": "rerank", "expand": True, "hint": "timeline", "cite": "pair", "budget": 6000,
                         "max_sessions": 5, "window": 1, "pool": 200, "rerank_k": 40, "older_mode": "strongest"},
    # round 1: pair-first packing (cited pair's best units, 2 backup sessions x 1 unit, then neighbours of the pair)
    "pk_bm25": {"retr": "bm25", "expand": True, "hint": "timeline", "cite": "pair", "pack": "pair", "budget": 4000,
                "extra": 2, "window": 1, "pool": 200},
    "pkq_bm25": {"retr": "bm25", "expand": True, "hint": "timeline", "cite": "pair", "pack": "pair", "budget": 4000,
                 "extra": 2, "window": 1, "pool": 200, "qpen": 0.3},
    "pkq3_bm25": {"retr": "bm25", "expand": True, "hint": "timeline", "cite": "pair", "pack": "pair", "budget": 5000,
                  "extra": 2, "window": 1, "pool": 200, "qpen": 0.3, "pair_units": 3},
    "pkc_bm25": {"retr": "bm25", "expand": True, "hint": "timeline", "cite": "pair", "pack": "pair", "budget": 5000,
                 "extra": 2, "window": 1, "pool": 200, "qpen": 0.3, "pair_units": 3, "cont": True},
    "pkv_bm25": {"retr": "bm25", "expand": True, "hint": "timeline", "cite": "pair", "pack": "pair", "budget": 5000,
                 "extra": 2, "window": 1, "pool": 200, "qpen": 0.3, "pair_units": 3, "cont": True, "need_val": True},
    "pkv3_bm25": {"retr": "bm25", "expand": True, "hint": "timeline", "cite": "pair", "pack": "pair", "budget": 5000,
                  "extra": 2, "window": 1, "pool": 200, "qpen": 0.3, "pair_units": 3, "cont": True, "need_val": True,
                  "cont_cov": 0.3},
    "pkv3b4_bm25": {"retr": "bm25", "expand": True, "hint": "timeline", "cite": "pair", "pack": "pair", "budget": 4000,
                    "extra": 2, "window": 1, "pool": 200, "qpen": 0.3, "pair_units": 3, "cont": True,
                    "need_val": True, "cont_cov": 0.3},
    "pkh_bm25": {"retr": "bm25", "expand": True, "hint": "timeline", "cite": "pair", "pack": "pair", "budget": 4000,
                 "extra": 2, "window": 1, "pool": 200, "qpen": 0.3, "pair_units": 3, "cont": True,
                 "need_val": True, "cont_cov": 0.3, "hpen": 0.4},
    "pkh_hybrid": {"retr": "hybrid", "expand": True, "hint": "timeline", "cite": "pair", "pack": "pair",
                   "budget": 4000, "extra": 2, "window": 1, "pool": 200, "qpen": 0.3, "pair_units": 3, "cont": True,
                   "need_val": True, "cont_cov": 0.3, "hpen": 0.4},
    "pkh_rerank": {"retr": "rerank", "expand": True, "hint": "timeline", "cite": "pair", "pack": "pair",
                   "budget": 4000, "extra": 2, "window": 1, "pool": 200, "qpen": 0.3, "pair_units": 3, "cont": True,
                   "need_val": True, "cont_cov": 0.3, "hpen": 0.4, "rerank_k": 30},
    "pkv3w0_bm25": {"retr": "bm25", "expand": True, "hint": "timeline", "cite": "pair", "pack": "pair", "budget": 5000,
                    "extra": 2, "window": 0, "pool": 200, "qpen": 0.3, "pair_units": 3, "cont": True,
                    "need_val": True, "cont_cov": 0.3},
    "pk_hybrid": {"retr": "hybrid", "expand": True, "hint": "timeline", "cite": "pair", "pack": "pair",
                  "budget": 4000, "extra": 2, "window": 1, "pool": 200},
    "pk_rerank": {"retr": "rerank", "expand": True, "hint": "timeline", "cite": "pair", "pack": "pair",
                  "budget": 4000, "extra": 2, "window": 1, "pool": 200, "rerank_k": 40},
}

# ------------------------------------------------------------------------------------------------------------------
# lexicon
# ------------------------------------------------------------------------------------------------------------------
_STOPW = set("""a an the of in on at to for from with by about as and or but if is are was were be been being do does
did have has had i me my mine myself we our ours us you your yours what which who whom whose when where why how many
much often time times currently current now these days day right recently most recent so far still previous
previously initially originally before after since that this there their they them it its am can could would should
will just any some other first last get got go going total number new old ago ever usually each every per tell than i'm i've i'd i'll you're you've it's that's don't didn't doesn't can't won't isn't aren't wasn't
we're we've they're
remind""".split())
_STOP = _STOPW | set(_stem(sorted(_STOPW)))

_NUMW = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
         "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand dozen "
         "half once twice first second third fourth fifth sixth seventh eighth ninth tenth").split()
_NUMW_RE = "|".join(_NUMW)
_DAYS = r"(?:mon|tues|wednes|thurs|fri|satur|sun)days?"
_MONTHS = ("january february march april may june july august september october november december "
           "monday tuesday wednesday thursday friday saturday sunday valentine christmas easter").split()

VAL_RE = {
    "number": re.compile(rf"(?<![\w/])(?:\$\s?\d[\d,]*(?:\.\d+)?k?|\d[\d,]*(?:\.\d+)?(?:\s?(?:k|gb|mb|tb|%|km|mi|lbs?|kg|"
                         rf"pounds|points|stars|followers|shillings|dollars|euros|hours?|minutes?))?|\d+\s?-\s?\d+|"
                         rf"(?:{_NUMW_RE})(?:[\s-](?:{_NUMW_RE}))*)\b", re.I),
    "time": re.compile(r"\b\d{1,2}(?::\d{2})?\s?(?:a\.?m\.?|p\.?m\.?)|\b\d{1,2}:\d{2}\b|\bnoon\b|\bmidnight\b", re.I),
    "day": re.compile(rf"\b{_DAYS}\b", re.I),
    "freq": re.compile(rf"\b(?:every\s+(?:other\s+)?(?:\w+\s+)?(?:day|week|month|morning|evening|night|weekend|"
                       rf"{_DAYS})s?|(?:once|twice|\w+\s+times)\s+(?:a|per|each)\s+(?:day|week|month)|daily|weekly|"
                       rf"biweekly|fortnightly|monthly|on\s+{_DAYS})\b", re.I),
    "duration": re.compile(rf"\b(?:\d+|{_NUMW_RE}|a|an|a few|several)\s+(?:minutes?|hours?|days?|weeks?|months?|years?)\b",
                           re.I),
    "name": re.compile(r"(?<!^)(?<![.!?]\s)\b[A-Z][\w'’\-]+(?:\s+(?:of|de|da|the|on|in)?\s?[A-Z][\w'’\-]+)*|"
                       r"['\"“‘][^'\"”’]{2,40}['\"”’]"),
    "place": re.compile(r"\b(?:in|at|under|above|on|from|inside|near|into|back to|moved to|trip to)\s+"
                        r"(?:(?:my|the|a|an|our|her|his)\s+\w+|[A-Z][\w-]+(?:\s+[A-Z][\w-]+)*)"),
}

CHANGE_RE = re.compile(r"\b(?:now|currently|these days|anymore|no longer|switched|switch|changed|change|moved|upgraded|"
                       r"downgraded|increased|decreased|cut back|reduced|renamed|replaced|retired|took over|hired|"
                       r"instead|shifted|promotion|promoted|went up|went down|bumped|actually|updated|new|another|"
                       r"\w+ more|added|just (?:got|reached|hit|finished|completed))\b", re.I)
OLD_RE = re.compile(r"\b(?:used to|old|previous(?:ly)?|former(?:ly)?|originally|at first|initially|last year|"
                    r"no longer|anymore|until)\b", re.I)
RECAP_RE = re.compile(r"\b(?:you (?:mentioned|said|told me|noted|shared|switched|moved|changed|increased|decreased|"
                      r"upgraded|renamed|started)|you've (?:mentioned|said|switched|moved|been)|I remember you|"
                      r"(?:is|are|has|was) now\b|your [\w' ]{1,40}? (?:is|are|has|was) now)", re.I)
DELTA_RE = re.compile(rf"\b(?:\d+|{_NUMW_RE}) (?:more|new|additional|extra|fewer|less)\b|\b(?:another|added|gained|"
                      rf"lost|sold|gave away)\b", re.I)

_REL = (r"(?:best friend|friend|sister|brother|sibling|mom|mum|mother|dad|father|parents?|coworker|co-worker|colleague|"
        r"neighbou?r|daughter|son|kids?|children|wife|husband|partner|boyfriend|girlfriend|fianc[ée]e?|cousin|aunt|"
        r"uncle|boss|roommate|flatmate|housemate|classmate|teammate|grandma|grandmother|grandpa|grandfather|niece|"
        r"nephew|in-laws?|client|student|running partner|landlord)")
_OWN_VERBS = (r"(?:has|have|had|is|was|says|said|told|tells|drinks|walks|runs|lives|pays|buys|uses|calls|named|goes|"
              r"went|keeps|needs|bought|got|started|swims|owns|takes|took|wants|used|gives|leads|works|plays|reads)")
OTHER_POSS_RE = re.compile(rf"\b{_REL}(?:\s+[A-Z][\w\-]+)?['’]s\b", re.I)
OTHER_SUBJ_RE = re.compile(rf"\b(?:my|your|our)\s+(?:\w+\s+)?{_REL}(?:\s+[A-Z][\w\-]+)?\s+(?:\w+\s+)?{_OWN_VERBS}\b",
                           re.I)
NAME_POSS_RE = re.compile(r"\b([A-Z][\wø\-]+)['’]s\s+(?=[A-Za-z])")
NAME_REL_RE = re.compile(rf"\b[A-Z][\wø\-]+['’]s\s+({_REL})\b", re.I)          # "Bjørn's daughter" -> daughter
SCOPE_RE = re.compile(r"(?:^|[:,;]\s*|\band\s+)the\s+[^.,;]{0,40}?\b(?:in|at|from)\s+(?:the\s+|our\s+)?"
                      r"([A-Z][\w\-]+)(?:\s+[A-Z][\w\-]+)*\s+(?:office|branch|location|site|campus|team|store|"
                      r"department|division|studio|clinic|school)\b", re.I)
PRON_SUBJ_RE = re.compile(r"^(?:\W*)(?:he|she|they|his|her|their)\b", re.I)
NAME_SUBJ_RE = re.compile(rf"(?:^\W*|\b(?:that|and|but|because)\s+)([A-Z][\wø\-]+)\s+(?:also\s+|still\s+|now\s+)?"
                          rf"{_OWN_VERBS}\b")                     # "Carlos drinks three cups ..." """
_NOT_NAMES = {"let", "it", "that", "what", "here", "there", "he", "she", "today", "year", "who", "where", "one",
              "everyone", "nobody", "somebody", "someone", "mother", "father", "valentine", "new"}

# rule-based synonym groups (stemmed on load); a hit on any member covers the question term
SYN_GROUPS = [
    "instructor teacher teach teaches taught teaching coach tutor",
    "title role position promotion promoted job",
    "rent lease",
    "gb gigabyte gigabytes data",
    "store shop market buy buying bought",
    "purchase purchased buy bought got new",
    "name named renamed call calls called",
    "team people members member hires staff",
    "live living lives moved move apartment flat",
    "often every weekly daily",
    "start starts begin begins",
    "walk walks walking kilometers kilometres km",
    "accountant accounting tax",
    "follower followers",
    "salary pay paid earn earning",
    "car vehicle drive",
    "doctor dr physician",
    "therapist therapy",
    "bike bikes bicycle",
]
_SYN = [set(_stem(g.split())) for g in SYN_GROUPS]
_SYN_TRIGGERS = [(re.compile(r"\b(?:" + "|".join(map(re.escape, g.split())) + r")\b", re.I), g.split())
                 for g in SYN_GROUPS]


def toks(s: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÿø](?:&[A-Za-z])?[A-Za-zÀ-ÿø'’\-]*|\d+", s)


def stems(s: str) -> list[str]:
    ws = [w.lower().replace("’", "'").strip("'").removesuffix("'s") for w in toks(s)]
    return [x for x in _stem(ws) if x not in _STOP and len(x) > 1]


def sstems(s: str) -> set[str]:
    """Sentence-side stems: stopwords kept, so rule synonyms such as got / new can match."""
    ws = [w.lower().strip("'’").removesuffix("'s").removesuffix("’s") for w in toks(s)]
    return set(_stem(ws)) | set(ws)


_SENT_SPLIT = re.compile(r"(?<![A-Z][a-z]\.)(?<!\b[A-Z]\.)(?<=[.!?])\s+|\n+")   # not after "Dr." / "St." / "J."


def sentences(text: str) -> list[str]:
    parts = _SENT_SPLIT.split(text)
    return [p.strip() for p in parts if p and p.strip()]


# ------------------------------------------------------------------------------------------------------------------
# question parsing
# ------------------------------------------------------------------------------------------------------------------
@dataclass
class QSpec:
    text: str
    atype: str
    direction: str                      # latest | previous | both | compare
    key: list[str]                      # content stems, question order, deduped
    alts: dict[str, set[str]]           # stem -> synonym stems
    caps: list[str]                     # capitalised non-initial tokens (proper nouns)
    q_owners: set[str]                  # relation words / names the question itself is about
    query: str                          # cleaned query for retrieval
    query_x: str                        # + synonyms
    head: str = ""                      # counted noun of "how many X" (stem); a mention without it is weak


_CUE_RE = re.compile(r"\b(now|currently|current|these days|right now|at the moment|most recently|most recent|"
                     r"recently|so far|still|anymore|latest|today|lately)\b", re.I)
_PREV_RE = re.compile(r"\b(initially|originally|at first|earlier|used to)\b|\bbefore (?:i|getting|the|my|we)\b|"
                      r"\bprevious(?:ly)?\b(?!\s+(?:company|employer|job|manager|colleague|coworker|apartment|house|"
                      r"school|chat|conversation))", re.I)
_COMPARE_RE = re.compile(r"\b(more|less|fewer|increase[ds]?|decrease[ds]?|higher|lower)\b.*\bor\b|"
                         r"\bthan (?:i did )?(?:previously|before)\b", re.I)


# answer-frame words: they shape the answer, they do not name the attribute ("what TYPE of lens", "did I INCREASE OR
# DECREASE the limit", "MORE or LESS water")
_FRAME_RE = re.compile(r"\b(?:type|kind|sort)s? of\b|\b(?:increase[ds]?|decrease[ds]?|more|less|fewer|higher|lower|"
                       r"bigger|smaller)\s+or\s+(?:increase[ds]?|decrease[ds]?|more|less|fewer|higher|lower|bigger|"
                       r"smaller)\b|\bor (?:more|less|fewer)\b|\b(?:the )?name of\b", re.I)


def answer_type(q: str) -> str:
    ql = q.lower()
    if _COMPARE_RE.search(q):
        if re.search(r"\b(?:frequent(?:ly)?|often)\b", ql):
            return "freq"
        if re.search(r"\b(?:more|less|fewer|increase[ds]?|decrease[ds]?|higher|lower)\b", ql):
            return "number"
    if "what time" in ql or re.search(r"\bwhen does\b.*\bstart", ql):
        return "time"
    if re.search(r"\b(what|which) day\b", ql):
        return "day"
    if re.search(r"\bhow (often|frequently)\b", ql):
        return "freq"
    if re.search(r"\bhow long\b", ql):
        return "duration"
    if re.search(r"\bhow (many|much|far)\b|\bwhat (?:is|was) (?:the |my )?(?:\w+\s+){0,2}(?:amount|number|total|score|"
                 r"record|rent|price|cost|level|count|percentage|salary|weight|time)\b", ql):
        return "number"
    if re.match(r"\s*where\b", ql):
        return "place"
    if re.match(r"\s*who\b", ql) or re.search(r"\bname\b|\b(what|which) (company|store|shop|brand|team|school)\b", ql):
        return "name"
    if re.match(r"\s*(is|are|do|does|did|have|has|was|were|can|am)\b", ql):
        return "yesno"
    return "other"


def direction(q: str) -> str:
    if q.count("?") >= 2 or (re.search(r"\bprevious(ly)?\b|\bwhen i (just )?started\b", q, re.I)
                             and re.search(r"\bnow\b", q, re.I)):
        return "both"
    if _COMPARE_RE.search(q):
        return "compare"
    if _PREV_RE.search(q):
        return "previous"
    return "latest"


_COMPARATIVES = set(_stem("more less fewer higher lower increase increased decrease decreased bigger smaller "
                          "longer shorter".split())) | {"more", "less", "fewer"}


def parse_question(q: str) -> QSpec:
    frame = _FRAME_RE.sub(" ", re.sub(r"\bhow long\b", " ", _CUE_RE.sub(" ", q), flags=re.I))
    key = list(dict.fromkeys(stems(frame))) or list(dict.fromkeys(stems(_CUE_RE.sub(" ", q))))
    if direction(q) == "compare":   # the comparative is the answer frame, not the attribute
        key = [w for w in key if w not in _COMPARATIVES] or key
    alts: dict[str, set[str]] = {}
    for w in key:
        for g in _SYN:
            if w in g:
                alts.setdefault(w, set()).update(g - {w})
    t = re.findall(r"[A-Za-zÀ-ÿø'’\-]+", q)
    caps = [w.strip("'’").removesuffix("'s").removesuffix("’s") for i, w in enumerate(t)
            if i > 0 and w[0].isupper() and w not in {"I", "I'm", "I've", "I'd", "Dr", "Mr", "Mrs", "Ms"} and len(w) > 2]
    owners = {m.group(0).lower() for m in re.finditer(_REL, q, re.I)} | {c.lower() for c in caps}
    query = re.sub(r"\s+", " ", _CUE_RE.sub(" ", q)).strip()
    extra = []
    for rx, words in _SYN_TRIGGERS:
        if rx.search(q):
            extra += [w for w in words if w.lower() not in q.lower()]
    query_x = query + (" " + " ".join(dict.fromkeys(extra)) if extra else "")
    head = ""
    hm = re.search(r"\bhow (?:many|much)\s+(?:of\s+)?(?:the\s+|my\s+)?([A-Za-z][\w'’&\-]*)", q, re.I)
    if hm:
        hs = stems(hm.group(1))
        head = hs[0] if hs and hs[0] in key else ""
    return QSpec(q, answer_type(q), direction(q), key, alts, caps, owners, query, query_x, head)


# ------------------------------------------------------------------------------------------------------------------
# sentence analysis
# ------------------------------------------------------------------------------------------------------------------
_CLAUSE_SPLIT = re.compile(r"\s*(?:[,;:—–]|\s-\s|\bso\b|\bbut\b|\bwhile\b|\bwhereas\b)\s*", re.I)


def _attr_clause(sent: str, spec: QSpec) -> str:
    """The clause of the sentence that carries most question terms ("My sister lives there, so I buy MY spices at X")."""
    parts = [c for c in _CLAUSE_SPLIT.split(sent) if c and c.strip()]
    if len(parts) < 2:
        return sent
    keys = set(spec.key) | set().union(*spec.alts.values()) if spec.alts else set(spec.key)
    hits = [len(keys & set(stems(c))) for c in parts]
    return parts[hits.index(max(hits))] if max(hits) > 0 else sent


def ownership(sent: str, spec: QSpec, role: str) -> str:
    """'other' if the attribute in this sentence belongs to someone the question is not about, else 'self'."""
    if role == "assistant" and not RECAP_RE.search(sent):
        return "assistant"            # assistant text that is not about the user (advice, generic facts)
    sent = _attr_clause(sent, spec)
    def foreign(tok: str) -> bool:
        tok = tok.lower()
        return not any(tok.startswith(o) or o.startswith(tok) for o in spec.q_owners)

    for m in OTHER_POSS_RE.finditer(sent):
        if foreign(re.sub(r"['’]s$", "", m.group(0)).split()[-1]):
            return "other"
    for m in OTHER_SUBJ_RE.finditer(sent):
        rel = re.search(_REL, m.group(0), re.I)
        if rel and foreign(rel.group(0)):
            return "other"
    for m in NAME_REL_RE.finditer(sent):
        if foreign(m.group(1)):
            return "other"
    for m in NAME_POSS_RE.finditer(sent):
        nm = m.group(1)
        if nm.lower() not in _NOT_NAMES and foreign(nm):
            return "other"
    if PRON_SUBJ_RE.search(sent) and not spec.q_owners:
        return "other"
    for m in SCOPE_RE.finditer(sent):          # "The UX team in the Munich office has eight people"
        if foreign(m.group(1)):
            return "other"
    for m in NAME_SUBJ_RE.finditer(sent):
        nm = m.group(1)
        if nm not in ("I", "My", "Your", "We", "Our", "It", "This", "That") and nm.lower() not in _NOT_NAMES and foreign(nm):
            return "other"
    return "self"


def values(sent: str, atype: str) -> list[str]:
    rx = VAL_RE.get(atype)
    if atype in ("yesno", "other"):
        return []
    out = [m.group(0).strip() for m in rx.finditer(sent)] if rx else []
    if atype == "number":   # drop dates / years that look like counts
        keep = []
        for m in rx.finditer(sent):
            v, tail = m.group(0).strip(), sent[m.end():m.end() + 6]
            if re.fullmatch(r"(19|20)\d\d", v) or v.lower() in ("first", "second", "once", "half", "a"):
                continue
            if v.lower() == "one" and (not re.match(r"\s+[a-z]", tail) or re.match(r"\s+of\b", tail)):
                continue                                   # "rent one", "one of them" are not counts
            keep.append(v)
        out = keep
    if atype == "name":
        out = [v for v in out if v.split()[0].lower() not in _NOT_NAMES and v.lower() not in _MONTHS]
    return out


@dataclass
class Mention:
    uid: int
    session_id: str
    sess_idx: int
    date_str: str
    turn_idx: int
    role: str
    sent: str
    cov: float
    vals: list[str]
    owner: str
    change: bool
    old: bool
    delta: bool
    score: float = 0.0
    sort_key: tuple = field(default_factory=tuple)
    caps_ok: bool = True        # some proper noun of the question occurs in this unit (or the question has none)


class _Idf:
    """Per-history document frequencies of stems over units (cached)."""
    _cache: dict = {}

    @classmethod
    def get(cls, hx):
        key = (getattr(hx, "split", "?"), getattr(hx, "history_id", id(hx)))
        if key not in cls._cache:
            df: dict[str, int] = {}
            ustems = set()
            allst = set()
            for u in hx.units:
                ss = set(stems(u.text))
                for w in ss:
                    df[w] = df.get(w, 0) + 1
                allst |= ss
                if u.role == "user":
                    ustems |= ss
            if len(cls._cache) > 8:
                cls._cache.clear()
            cls._cache[key] = (df, len(hx.units), ustems, allst)
        return cls._cache[key]


def coverage(sent_stems: set[str], spec: QSpec, idf: dict[str, float]) -> float:
    if not spec.key:
        return 0.0
    tot = sum(idf.get(w, 1.0) for w in spec.key)
    got = sum(idf.get(w, 1.0) for w in spec.key if w in sent_stems or (spec.alts.get(w, set()) & sent_stems))
    return got / tot if tot else 0.0


_PURE_Q = re.compile(r"^\W*(?:(?:so|and|but|also|ok|okay|well),?\s+)?(?:do|does|did|can|could|should|would|will|is|are|"
                     r"was|were|what|how|which|who|where|when|why|any|have|has)\b", re.I)


def extract_mentions(hx, spec: QSpec, uids: list[int], rank: dict[int, int], cov_min: float = 0.34,
                     qpen: float = 0.0, hpen: float = 0.0) -> list[Mention]:
    df, n, _, _ = _Idf.get(hx)
    idf = {w: (math.log((n + 1) / (df.get(w, 0) + 0.5)) if n >= 20 else 1.0) for w in spec.key}
    caps = [c for c in spec.caps if c.lower() not in _MONTHS]
    out = []
    for uid in uids:
        u = hx.units[uid]
        ctx_st = sstems(u.ctx) if getattr(u, "ctx", "") else set()
        sents = sentences(u.text)
        for si, s in enumerate(sents):
            st = sstems(s)
            cov = coverage(st, spec, idf)
            if cov < cov_min:
                # short replies ("She moved to Chicago.") inherit coverage from the assistant question before them
                if not (si == 0 and ctx_st and coverage(st | ctx_st, spec, idf) >= cov_min + 0.15 and len(s) < 120):
                    continue
                cov = coverage(st | ctx_st, spec, idf) - 0.1
            vals = values(s, spec.atype)
            if not vals and si + 1 < len(sents) and spec.atype not in ("yesno", "other"):
                nxt = values(sents[si + 1], spec.atype)
                if nxt and coverage(sstems(sents[si + 1]), spec, idf) >= 0.2:
                    s, vals = f"{s} {sents[si + 1]}", nxt      # "...charity 5K run... By the way, ... best time of 25:50"
                    cov = max(cov, coverage(st | sstems(sents[si + 1]), spec, idf))
            own = ownership(s, spec, u.role)
            m = Mention(uid, u.session_id, u.sess_idx, u.date_str, u.turn_idx, u.role, s, cov, vals, own,
                        bool(CHANGE_RE.search(s)), bool(OLD_RE.search(s)), bool(DELTA_RE.search(s)))
            r = rank.get(uid, 999)
            no_head = bool(spec.head) and not ({spec.head} | spec.alts.get(spec.head, set())) & (st | ctx_st)
            m.score = (cov + (0.25 if vals or spec.atype in ("yesno", "other") else 0.0) + (0.08 if m.change else 0.0)
                       + 0.3 / (1 + r / 5) - (0.6 if own == "other" else 0.0) - (0.35 if own == "assistant" else 0.0)
                       - (qpen if u.role == "user" and s.rstrip().endswith("?") and (not vals or _PURE_Q.match(s))
                          else 0.0) - (hpen if no_head else 0.0))
            m.sort_key = (u.date, u.sess_idx, u.turn_idx, si)
            m.caps_ok = not caps or any(c.lower() in u.text.lower() for c in caps)
            out.append(m)
    return out


@dataclass
class Timeline:
    self_m: list[Mention]       # user's own mentions, chronological, one best per session
    other_m: list[Mention]
    newest: Mention | None
    older: Mention | None


_WN = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                   "fifteen sixteen seventeen eighteen nineteen twenty".split())}
_WN.update({"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
            "hundred": 100, "dozen": 12, "once": 1, "twice": 2})


def num_of(v: str) -> float | None:
    m = re.search(r"\d[\d,]*(?:\.\d+)?", v)
    if m:
        try:
            return float(m.group(0).replace(",", ""))
        except ValueError:
            return None
    for w in re.findall(r"[a-z]+", v.lower()):
        if w in _WN:
            return float(_WN[w])
    return None


def unit_of(sent: str, v: str) -> str | None:
    """The content word right after a value ("1250 followers" -> follow, "4 weeks" -> week); None if absent."""
    m = re.search(re.escape(v) + r"\s+([A-Za-z]+)", sent)
    w = m.group(1).lower() if m else ""
    if not m:
        parts = v.split()
        w = parts[-1].lower() if len(parts) > 1 and not re.search(r"\d", parts[-1]) else ""
    if not w or w in _STOPW or w in _WN:
        return None
    return _stem([w])[0]


def same_kind(a: "Mention", b: "Mention") -> bool:
    """Same quantity: numbers within a factor of 5 whose units (word after the number) do not conflict."""
    for va in a.vals:
        for vb in b.vals:
            x, y = num_of(va), num_of(vb)
            if not x or not y or not 0.2 <= y / x <= 5:
                continue
            ua, ub = unit_of(a.sent, va), unit_of(b.sent, vb)
            if ua and ub and ua != ub:
                continue
            return True
    return False


def build_timeline(mentions: list[Mention], strong: float = 0.75, rel: float = 0.7, older_mode: str = "recent3",
                   cont: bool = False, cont_cov: float = 0.4, need_val: bool = False) -> Timeline:
    own = [m for m in mentions if m.owner == "self"]
    other = [m for m in mentions if m.owner == "other"]
    best: dict[str, Mention] = {}
    for m in own:
        if m.session_id not in best or m.score > best[m.session_id].score:
            best[m.session_id] = m
    tl = sorted(best.values(), key=lambda m: m.sort_key)
    top = max((m.score for m in tl), default=0.0)
    strong = max(strong, rel * top)          # relative: noise mentions with partial coverage must not become "newest"
    anchor = max((m for m in tl if m.vals), key=lambda m: m.score, default=None) if cont else None

    def continues(m):       # a later restatement of the anchor's quantity ("1250 followers" -> "close to 1300 now")
        return (anchor is not None and m.vals and m.sort_key > anchor.sort_key and m.cov >= cont_cov
                and m.score >= 0.55 and m.caps_ok and same_kind(anchor, m))

    strong_m = [m for m in tl if m.score >= strong or continues(m)] or sorted(tl, key=lambda m: -m.score)[:2]
    if need_val and any(m.vals for m in strong_m):      # a quantity question needs a mention that states one
        strong_m = [m for m in strong_m if m.vals]
    strong_m.sort(key=lambda m: m.sort_key)
    newest = strong_m[-1] if strong_m else None
    older = None
    if newest is not None:
        before = [m for m in tl if m.sort_key < newest.sort_key and m.score >= strong - 0.25]
        nv = {v.lower() for v in newest.vals}
        diff = [m for m in before if m.vals and not ({v.lower() for v in m.vals} <= nv)]
        pick = diff or before
        if pick:
            if older_mode == "strongest":     # strongest earlier mention anywhere (better on test-style, worse dev200)
                older = max(pick, key=lambda m: (round(m.score, 1), m.sort_key))
            else:                             # strongest of the last 3 earlier mentions
                older = max(pick[-3:], key=lambda m: m.score)
    return Timeline(tl, other, newest, older)


# ------------------------------------------------------------------------------------------------------------------
# hints and abstention
# ------------------------------------------------------------------------------------------------------------------
_DIR_HINT = {
    "latest": "This asks for the CURRENT value. It changed over time: the most recent statement (latest session date) "
              "about the user's own value wins over older ones.",
    "previous": "This asks for the EARLIER value, the one that held before the most recent change; do not answer "
                "with the newest value.",
    "both": "Give both values: the earlier one and the current (latest) one.",
    "compare": "Compare the earlier value with the latest one and answer the direction of the change.",
}


def _attr_label(spec: QSpec) -> str:
    q = _CUE_RE.sub(" ", spec.text)
    m = re.search(r"\b(?:my|our)\s+((?:[\w'’\-]+\s+){0,3}[\w'’\-]+?)(?=\s+(?:now|currently|these|right|do|did|have|is|"
                  r"was|on|in|at|for|with|from)\b|\?|$)", q, re.I)
    return m.group(1).strip() if m else "attribute"


def _quote(s: str, n: int = 170) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def make_hint(spec: QSpec, tl: Timeline, mode: str, absent_all: list[str], absent_user: list[str],
              max_quotes: int = 4) -> str:
    if mode == "none":
        return ""
    parts = [_DIR_HINT[spec.direction]]
    if mode == "timeline" and tl.self_m:
        top = max(m.score for m in tl.self_m)
        pair = [m for m in (tl.older, tl.newest) if m is not None]
        valued = spec.atype in ("yesno", "other") or not any(m.vals for m in pair)
        rest = [m for m in tl.self_m if m.score >= 0.7 * top and m not in pair and (valued or m.vals)]
        keep = sorted(rest[-max(0, max_quotes - len(pair)):] + pair, key=lambda m: m.sort_key)
        if len(keep) >= 2:
            lines = [f'- {m.date_str[:10]}{" (assistant recap)" if m.role == "assistant" else ""}: "{_quote(m.sent)}"'
                     for m in keep]
            parts.append("Dated mentions found (oldest first):\n" + "\n".join(lines))
        if tl.newest is not None and tl.newest.delta and spec.atype == "number":
            parts.append("If a later statement only gives a change (e.g. '2 more'), apply it to the earlier value.")
    if tl.other_m:
        parts.append("Ignore values that belong to other people (friend, relative, coworker, neighbour) "
                     "unless the question is about them.")
    if absent_all:
        parts.append("Note: " + ", ".join(f'"{w}"' for w in absent_all) + " never appears in the conversation history.")
    elif absent_user:
        parts.append("Note: the user never mentions " + ", ".join(f'"{w}"' for w in absent_user) + ".")
    return "\n".join(parts)


def abstain_prob(spec: QSpec, hx, tl: Timeline, mentions: list[Mention]) -> tuple[float, list[str], list[str], float]:
    df, n, ustems, allst = _Idf.get(hx)
    caps = [c for c in spec.caps if c.lower() not in _MONTHS]
    cst = {c: (_stem([c.lower()])[0] if c else c) for c in caps}
    absent_all = [c for c in caps if cst[c] not in allst]
    absent_user = [c for c in caps if cst[c] not in ustems and c not in absent_all]
    best_cov = max((m.cov for m in mentions if m.role == "user"), default=0.0)
    p = 0.06 + 0.55 * max(0.0, 0.9 - best_cov) / 0.9
    if absent_all:
        p += 0.4
    elif absent_user:
        p += 0.25
    if any(w not in ustems for w in spec.key) and not absent_user and not absent_all:
        p += 0.08
    if not tl.self_m and tl.other_m:
        p += 0.2
    if tl.newest is not None and tl.older is not None and tl.newest.vals:
        p -= 0.08
    return max(0.02, min(0.95, p)), absent_all, absent_user, best_cov


# ------------------------------------------------------------------------------------------------------------------
# retrieval
# ------------------------------------------------------------------------------------------------------------------
def _rrf(lists: list[list[tuple[int, float]]], k: int = 60) -> list[int]:
    sc: dict[int, float] = {}
    for lst in lists:
        for r, (uid, _) in enumerate(lst):
            sc[uid] = sc.get(uid, 0.0) + 1.0 / (k + r + 1)
    return [u for u, _ in sorted(sc.items(), key=lambda x: -x[1])]


def retrieve(q, hx, spec: QSpec, p: dict) -> tuple[list[int], dict]:
    pool, dbg = p.get("pool", 200), {}
    lists = [hx.bm25(spec.query, k=pool)]
    if p.get("expand") and spec.query_x != spec.query:
        lists.append(hx.bm25(spec.query_x, k=pool))
    if p.get("retr") in ("hybrid", "rerank"):
        try:
            lists.append(hx.dense(spec.query, k=pool))
        except Exception as e:  # model server down -> BM25 only, recorded
            dbg["fallback"] = f"dense: {e!r}"[:200]
    ranking = _rrf(lists)
    if p.get("retr") == "rerank" and ranking:
        k = p.get("rerank_k", 40)
        try:
            rr = hx.rerank(q.question, ranking[:k])
            ranking = [u for u, _ in rr] + ranking[k:]
        except Exception as e:
            dbg["fallback"] = f"rerank: {e!r}"[:200]
    return ranking, dbg


# ------------------------------------------------------------------------------------------------------------------
# lens entry point
# ------------------------------------------------------------------------------------------------------------------
def analyse(q, hx, p: dict):
    spec = parse_question(q.question)
    ranking, dbg = retrieve(q, hx, spec, p)
    rank = {u: i for i, u in enumerate(ranking)}
    cand = ranking[: p.get("mention_pool", 80)]
    mentions = extract_mentions(hx, spec, cand, rank, cov_min=p.get("cov_min", 0.34), qpen=p.get("qpen", 0.0),
                                hpen=p.get("hpen", 0.0))
    tl = build_timeline(mentions, strong=p.get("strong", 0.75), rel=p.get("rel", 0.7),
                        older_mode=p.get("older_mode", "recent3"), cont=p.get("cont", False),
                        cont_cov=p.get("cont_cov", 0.4),
                        need_val=p.get("need_val", False) and spec.atype in ("number", "time", "duration", "freq", "day"))
    return spec, ranking, mentions, tl, dbg


def _sess_units(hx, sid: str, mentions: list["Mention"], ranking: list[int], n_units: int = 1) -> list[int]:
    """Units of one session in priority order: its strongest own (user or recap) mention units from distinct turns
    (score >= 0.6 x best), else its best-ranked unit; a short reply is preceded by the unit before it (the assistant
    question it answers)."""
    ms = sorted((m for m in mentions if m.session_id == sid), key=lambda m: -m.score)
    own = [m for m in ms if m.owner == "self"] or ms
    out: list[int] = []
    turns = set()
    for m in own:
        if len(out) >= n_units or m.score < 0.6 * own[0].score:
            break
        if hx.units[m.uid].turn_id not in turns:
            turns.add(hx.units[m.uid].turn_id)
            u = m.uid
            if len(hx.units[u].text) < 160 and u > 0 and hx.units[u - 1].session_id == sid and u - 1 not in out:
                out.append(u - 1)
            out.append(u)
    if not out:
        out = [u for u in ranking if hx.units[u].session_id == sid][:1]
    return list(dict.fromkeys(out))


def assemble(q, hx, groups: list[tuple[str, list[int]]], fill: list[int], budget: int, hint: str):
    """Pair-first packing: whole groups (session -> units) in priority order while they fit, then single fill units
    (neighbours of the cited mentions) while they fit. Passages in chronological order."""
    from collections import OrderedDict

    from core.pack import message_chars, render
    from core.types import Passage

    def passages_for(sel):
        out = []
        for sid in sorted(sel, key=lambda s: hx.sess_by_id[s]["sess_idx"]):
            text, _ = render(hx, sorted(sel[sid]))
            out.append(Passage(id=sid, date=hx.sess_by_id[sid]["date_str"], text=text))
        return out

    chosen: "OrderedDict[str, set[int]]" = OrderedDict()
    chars = message_chars(q, [], hint)
    for sid, uids in groups:
        for cand in [uids[:n] for n in range(len(uids), 0, -1)]:
            trial = OrderedDict((k, set(v)) for k, v in chosen.items())
            trial.setdefault(sid, set()).update(cand)
            c = message_chars(q, passages_for(trial), hint)
            if c <= budget:
                chosen, chars = trial, c
                break
    for uid in fill:
        sid = hx.units[uid].session_id
        if sid not in chosen or uid in chosen[sid]:
            continue
        trial = OrderedDict((k, set(v)) for k, v in chosen.items())
        trial[sid].add(uid)
        c = message_chars(q, passages_for(trial), hint)
        if c <= budget:
            chosen, chars = trial, c
    passages = passages_for(chosen)
    included: set[str] = set()
    for sid, uids in chosen.items():
        included |= {hx.units[i].turn_id for i in uids}
    return passages, included, chars


def build(q, hx, **params) -> EvidencePack:
    from core.pack import build_pack

    p = {**VARIANTS["tl_rerank"], **params}
    spec, ranking, mentions, tl, dbg = analyse(q, hx, p)
    ap, absent_all, absent_user, best_cov = abstain_prob(spec, hx, tl, mentions)

    # session choice for citation
    if p.get("cite") == "pair" and tl.newest is not None:
        pair = [m.session_id for m in (tl.older, tl.newest) if m is not None]
    else:
        pair = []
    if len(pair) < 2:   # fill with the best-ranked other sessions
        for uid in ranking:
            sid = hx.units[uid].session_id
            if sid not in pair:
                pair.append(sid)
            if len(pair) >= 2:
                break

    # unit order for the pack: cited sessions' mention units, other strong self mentions, other mentions, ranking
    order: list[int] = []
    by_score = sorted(mentions, key=lambda m: -m.score)
    for m in by_score:
        if m.session_id in pair:
            order.append(m.uid)
    for m in by_score:
        if m.owner == "self":
            order.append(m.uid)
    order += [m.uid for m in by_score] + ranking
    order = list(dict.fromkeys(order))
    if not any(hx.units[u].session_id in pair for u in order[:1]):
        order = [u for s in pair for u in ranking if hx.units[u].session_id == s][:2] + order
        order = list(dict.fromkeys(order))

    hint = make_hint(spec, tl, p.get("hint", "timeline"), absent_all, absent_user)
    if p.get("pack") == "pair":
        # cited pair first (best mention units), then `extra` backup sessions (own mentions, then ranking), one unit
        # each; then +-window neighbours of the cited units while the budget lasts
        groups = [(sid, _sess_units(hx, sid, mentions, ranking, p.get("pair_units", 2))) for sid in pair]
        backup: list[str] = []
        for m in sorted(tl.self_m, key=lambda m: -m.score):
            if m.session_id not in pair and m.session_id not in backup:
                backup.append(m.session_id)
        for uid in ranking[:60]:
            sid = hx.units[uid].session_id
            if sid not in pair and sid not in backup:
                backup.append(sid)
        groups += [(sid, _sess_units(hx, sid, mentions, ranking, 1)) for sid in backup[: p.get("extra", 2)]]
        w = p.get("window", 1)
        fill = [n for _, us in groups[: len(pair)] for u in us for n in hx.neighbors(u, w, w)] if w else []
        passages, included, chars = assemble(q, hx, groups, fill, p.get("budget", 4000), hint)
    else:
        passages, included, chars = build_pack(q, hx, order, budget=p.get("budget", 6000), window=p.get("window", 1),
                                               order="chrono", hint=hint, max_sessions=p.get("max_sessions", 5))
    ids = {ps.id for ps in passages if ps.id}
    cite = [s for s in sorted(pair, key=lambda s: hx.sess_by_id[s]["date"]) if s in ids] or None

    computed = None
    if (spec.direction == "latest" and spec.atype == "number" and tl.newest is not None and len(tl.newest.vals) == 1
            and not tl.newest.delta):
        computed = tl.newest.vals[0]

    dbg.update({"ranking": ranking[:300], "atype": spec.atype, "direction": spec.direction, "key": spec.key,
                "best_cov": round(best_cov, 3), "absent_all": absent_all, "absent_user": absent_user,
                "timeline": [(m.date_str[:10], m.role, m.owner, round(m.score, 2), m.vals[:3], _quote(m.sent, 90))
                             for m in tl.self_m[-6:]],
                "other": [(m.date_str[:10], _quote(m.sent, 80)) for m in tl.other_m[:4]],
                "pair": pair, "chars": chars})
    return EvidencePack(question_id=q.question_id, variant=params.get("_variant", ""), route="ku",
                        passages=passages, hint=hint, cite_plan=cite, abstain_p=round(ap, 3),
                        included_turns=included, computed=computed, debug=dbg)


# ------------------------------------------------------------------------------------------------------------------
# self-test (no model server, no core.pack needed)
# ------------------------------------------------------------------------------------------------------------------
class _MiniHx:
    """Tiny stand-in for HistoryIndex built from gold turns (self-test only)."""

    def __init__(self, turns: list[dict]):
        from datetime import datetime
        from core.types import Unit
        self.split, self.history_id = "selftest", str(id(turns))
        self.units = []
        for i, t in enumerate(turns):
            d = datetime.strptime(t["date"], "%Y/%m/%d (%a) %H:%M")
            self.units.append(Unit(i, t["session_id"], i, d, t["date"], f"t{i}", 0, t.get("role", "user"), 0,
                                   t["text"], t.get("prev_turn_tail", "")[-220:]))


def _selftest_samples():
    import json
    rows = [json.loads(l) for l in open("runs/samples/ku.jsonl")]
    print("== question parsing ==")
    for r in rows:
        s = parse_question(r["question"])
        print(f"  [{s.atype:8s}|{s.direction:8s}] {r['question'][:80]}  key={s.key[:6]} caps={s.caps} "
              f"x={s.query_x[len(s.query):][:40]!r}")
    print("== timeline on gold turns (dev samples) ==")
    ok = tot = 0
    for r in rows:
        if r["split"] != "dev" or r.get("abstain") or not r.get("gold_turns"):
            continue
        spec = parse_question(r["question"])
        hx = _MiniHx(r["gold_turns"])
        ms = extract_mentions(hx, spec, list(range(len(hx.units))), {i: 0 for i in range(len(hx.units))})
        tl = build_timeline(ms)
        newest_gold = max(r["evidence"], key=lambda e: e["date"])["session_id"]
        hit = tl.newest is not None and tl.newest.session_id == newest_gold
        ok += hit
        tot += 1
        print(f"  {'OK ' if hit else 'BAD'} {r['question'][:60]:60s} gold={str(r['answer'])[:25]:25s} "
              f"newest={(tl.newest.vals[:2], _quote(tl.newest.sent, 60)) if tl.newest else None}")
    print(f"  newest = newest gold session: {ok}/{tot}")
    print("== ownership on test-style sentences ==")
    spec = parse_question("How many people are on my UX team now?")
    for s in ["My UX team has six people right now, and we are all on the project kickoff call.",
              "That reminds me: My friend Clara's UX team has six people, which makes their research critiques "
              "very focused.",
              "My UX team now has eight people after the two new hires started today.",
              "My sister Amina is still on a 15GB mobile data plan.",
              "He drinks three cups of coffee every morning and says he won't give it up.",
              "Oh, and Your daughter said she needs two cups of coffee before starting work.."]:
        print(f"  {ownership(s, spec, 'user'):6s} {s[:90]}")
    spec2 = parse_question("How many Icelandic horses do my neighbor Bjørn and I have in total right now?")
    for s in ["By the way, Your neighbor Bjørn has 5 Icelandic horses.", "Bjørn's daughter has 2 Icelandic horses.",
              "My sister has 9 Icelandic horses on her farm.", "By the way, I bought 2 more Icelandic horses."]:
        print(f"  {ownership(s, spec2, 'user'):6s} {s[:90]}")


def _selftest_bm25(split: str = "dev"):
    """Session-pair check with BM25 only: does the [older, newest] pair equal the gold evidence?"""
    from core.data import gold, questions
    from core.index import HistoryIndex
    g = gold(split)
    qs = {q.question_id: q for q in questions(split)}
    n = f1s = newest_ok = top2_f1 = 0
    p = {**VARIANTS["tl_bm25"]}
    for qid, x in g.items():
        if x["question_type"] != "knowledge-update" or x["abstain"]:
            continue
        q = qs[qid]
        hx = HistoryIndex.load(split, q.history_id)
        spec, ranking, mentions, tl, _ = analyse(q, hx, p)
        pair = [m.session_id for m in (tl.older, tl.newest) if m is not None]
        for uid in ranking:
            if len(pair) >= 2:
                break
            if hx.units[uid].session_id not in pair:
                pair.append(hx.units[uid].session_id)
        G = set(x["evidence"])
        newest_g = max(G, key=lambda s: hx.sess_by_id[s]["date"])

        def f1(P):
            P = set(P)
            tp = len(P & G)
            return 0.0 if not tp else 2 * tp / (len(P) + len(G))
        top2 = []
        for uid in hx.bm25(spec.query, k=300, roles="user"):
            sid = hx.units[uid[0]].session_id
            if sid not in top2:
                top2.append(sid)
            if len(top2) == 2:
                break
        n += 1
        f1s += f1(pair)
        top2_f1 += f1(top2)
        newest_ok += newest_g in pair
        if f1(pair) < 1:
            print(f"  F1={f1(pair):.2f} {q.question[:70]} | ans={str(x['answer'])[:30]} | tl={[(m.date_str[:10], m.vals[:2], round(m.score, 2)) for m in tl.self_m[-4:]]}")
    print(f"{split}: n={n} pair-F1={f1s / n:.3f} newest-in-pair={newest_ok}/{n} | bm25-user-top2 F1={top2_f1 / n:.3f}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--bm25":
        for sp in sys.argv[2:] or ["dev"]:
            _selftest_bm25(sp)
    else:
        _selftest_samples()
