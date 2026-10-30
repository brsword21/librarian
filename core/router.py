"""Question -> type guess. Rules from dev and test phrasing; confidence is crude. Lenses must not rely on it alone
(dev knowledge-update questions rarely carry a cue)."""
from __future__ import annotations

import re

_T = re.compile(r"days? (apart|after|before|ago|passed|between|had passed)|how (long|many (days|weeks|months|years))\b.*\b(ago|passed|between|before|after|when|since|had i|have i been)"
                r"|\bago\b|which .*\b(first|earlier|later|last)\b|in what order|order of|what was the date|what date|when did i"
                r"|how many (days|weeks|months|years) (ago|passed|had|have|did|between)|before or after|\bfirst\b.*\bor\b", re.I)
_A = re.compile(r"\byou (recommend|suggest|mention|told|said|gave|provided|list|shared|proposed|came up)|\byour (recommendation|suggestion|advice)"
                r"|our (previous|last|earlier) (chat|conversation|discussion)|remind me (of )?what you", re.I)
_K = re.compile(r"\b(now|currently|current|these days|right now|still|latest|most recent|at the moment|anymore|so far)\b", re.I)
_M = re.compile(r"^(how many|how much)|\b(in total|total|combined|altogether|all together|sum|difference|average|percentage|in all)\b", re.I)


def route(question: str) -> tuple[str, float]:
    q = question.strip()
    if _A.search(q):
        return "ssa", 0.9
    if _T.search(q):
        return "temporal", 0.8
    if _K.search(q):
        return ("multi" if _M.search(q) and not re.search(r"\b(now|right now|currently)\b", q, re.I) else "ku"), 0.6
    if _M.search(q):
        return "multi", 0.6
    return "ssu", 0.4
