"""Where KU gold turns sit and how the update is phrased (dev / dev200). Plain python + core.index BM25 only."""
import re, sys, math
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from core.data import gold, questions
from core.gold_turns import gold_turns
from core.index import HistoryIndex

split = sys.argv[1] if len(sys.argv) > 1 else "dev"
g = gold(split); gt = gold_turns()
qs = [q for q in questions(split) if g[q.question_id]["question_type"] == "knowledge-update"]
OLDQ = re.compile(r"\b(previous(ly)?|initial(ly)?|before|earlier|first|originally|used to|old)\b", re.I)
CHANGE = re.compile(r"\b(now|currently|current|switched|changed|moved|upgraded|increased|decreased|new|actually|anymore|no longer|instead|so far|up to|just|recently|again|since)\b", re.I)
role, tidx, chunk0, gap_days, change_new, change_old, oldq = Counter(), [], 0, [], 0, 0, 0
n_turns = 0
for q in qs:
    gg = g[q.question_id]
    if gg["abstain"]:
        continue
    oldq += bool(OLDQ.search(q.question))
    hx = HistoryIndex.load(split, q.history_id)
    ev = sorted(gg["evidence"], key=lambda s: hx.sess_by_id[s]["sess_idx"])
    d = [hx.sess_by_id[s]["date"] for s in ev]
    gap_days.append((d[-1] - d[0]).days)
    for tid in gt.get(q.question_id, []):
        uids = hx.turn_units(tid)
        if not uids:
            continue
        u = hx.units[uids[0]]
        n_turns += 1
        role[u.role] += 1
        tidx.append(u.turn_idx)
        text = " ".join(hx.units[i].text for i in uids)
        if u.session_id == ev[-1]:
            change_new += bool(CHANGE.search(text))
        else:
            change_old += bool(CHANGE.search(text))
n = sum(1 for q in qs if not g[q.question_id]["abstain"])
print(split, "answerable", n, "gold turns", n_turns)
print("role", dict(role))
print("turn_idx hist", Counter(min(t, 10) for t in tidx))
gap_days.sort()
print("days old->new: min/med/max", gap_days[0], gap_days[len(gap_days)//2], gap_days[-1])
print("question asks for the OLD value (regex):", oldq)
print("change-cue in new gold turn:", change_new, "| in old gold turn:", change_old)
