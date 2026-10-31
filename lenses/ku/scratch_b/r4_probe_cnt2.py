"""Probe: statement-form query + dense/CE over user units with a completion/event verb."""
import re, sys
from core.index import HistoryIndex
split, hid, qtext = sys.argv[1:4]
hx = HistoryIndex.load(split, hid)
m = re.match(r"\s*how many\s+(.+?)\s+(?:have|has|did)\s+(i|we)\s+(.+?)\??$", qtext, re.I)
stmt = f"{m.group(2)} {m.group(3)} the {m.group(1)}" if m else qtext
stmt = re.sub(r"\b(so far|in total|completely)\b", "", stmt).strip()
print("STATEMENT:", stmt)
DONE = re.compile(r"\b(finished|done|wrapped up|completed?|refinished|finally)\b", re.I)
cand = [u for u in hx.units if u.role == "user" and DONE.search(u.text)]
ds = hx.dense_texts(stmt, [u.text for u in cand])
ce = hx.rerank_texts(stmt, [u.text for u in cand])
order = sorted(range(len(cand)), key=lambda i: -ds[i])
for r, i in enumerate(order[:15]):
    print(f"dense#{r:2d} {ds[i]:.3f} ce={ce[i]:6.2f} {cand[i].date_str[:10]} {cand[i].text[:150]!r}")
print("by CE:")
for r, i in enumerate(sorted(range(len(cand)), key=lambda i: -ce[i])[:10]):
    print(f"ce#{r:2d} {ce[i]:6.2f} dense={ds[i]:.3f} {cand[i].date_str[:10]} {cand[i].text[:150]!r}")
