"""List all dev / dev200 ssu questions with gold answer and gold user turn location."""
import json, sys, re
sys.path.insert(0, '.')
from core.data import questions, gold, history
from core.gold_turns import gold_turns

split = sys.argv[1] if len(sys.argv) > 1 else 'dev'
G = gold(split); GT = gold_turns()
qs = [q for q in questions(split) if G.get(q.question_id, {}).get('question_type') == 'single-session-user']
print(split, len(qs), 'ssu questions;', sum(G[q.question_id]['abstain'] for q in qs), 'abstain')
for q in qs:
    g = G[q.question_id]
    h = history(split, q.history_id)
    tid2 = {}
    for si, s in enumerate(h['sessions']):
        for ti, t in enumerate(s['turns']):
            tid2[t['turn_id']] = (si, ti, t['role'], s['session_id'], t['content'])
    gts = GT.get(q.question_id, [])
    locs = [(tid2[t][0], tid2[t][1], tid2[t][2]) for t in gts if t in tid2]
    print(f"- {q.question_id} [{len(h['sessions'])}s] Q: {q.question} | A: {g['answer'][:80]} | abst={g['abstain']} | gold turns(sess_idx,turn_idx,role)={locs}")
