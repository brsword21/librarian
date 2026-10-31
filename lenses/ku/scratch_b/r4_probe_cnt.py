"""Probe: rank units for a count-of-instances ku question; where do completion statements land?"""
import re, sys
from core.index import HistoryIndex
split, hid, qtext, pat = sys.argv[1:5]
hx = HistoryIndex.load(split, hid)
rx = re.compile(pat, re.I)
hyb = [u for u, _ in hx.hybrid(qtext, k=300)]
rk = {u: i for i, u in enumerate(hyb)}
DONE = re.compile(r"\b(finished|done|wrapped up|completed?|refinished|finally (?:primed|patched))\b", re.I)
cand = [u.uid for u in hx.units if DONE.search(u.text) and rx.search(u.text)]
ce = dict(hx.rerank(qtext, cand)) if cand else {}
for u in sorted(cand, key=lambda x: -ce[x]):
    un = hx.units[u]
    print(f"ce={ce[u]:6.2f} hyb_rank={rk.get(u, '-'):>4} {un.date_str[:10]} {un.role[:4]} {un.text[:160]!r}")
