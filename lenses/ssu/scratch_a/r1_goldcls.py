"""Classify the gold user units of every answerable ssu question; print the ones the structure would demote.
usage: python lenses/ssu/scratch_a/r1_goldcls.py dev|dev200"""
import sys
sys.path.insert(0, '.')
from core.index import HistoryIndex
from core.data import questions, gold
from core.gold_turns import gold_turns
from lenses.ssu.a_owner import parse_question, unit_class
split = sys.argv[1]
G = gold(split); GT = gold_turns()
n = bad = 0
for q in questions(split):
    g = G[q.question_id]
    if g['abstain'] or g['question_type'] != 'single-session-user':
        continue
    hx = HistoryIndex.load(split, q.history_id)
    qp = parse_question(q.question)
    for t in GT.get(q.question_id, []):
        for uid in hx.turn_units(t):
            u = hx.units[uid]
            if u.role != 'user':
                continue
            sc = unit_class(u, qp)
            n += 1
            dem = sc.owner == 'mismatch' or sc.polarity in ('neg', 'plan', 'stale') or not sc.valid
            if dem:
                bad += 1
                print(f"{q.question_id} {q.question} | owner={sc.owner}({sc.owner_why}) pol={sc.polarity} head={sc.head_hit} "
                      f"verb={sc.verb_hit} valid={sc.valid}\n    {sc.sent[:220]}")
print('gold user units', n, 'demoted', bad)
