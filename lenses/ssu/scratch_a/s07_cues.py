"""How discriminative are 'aside-disclosure' cues and first-person statements? gold user turns vs all user turns."""
import sys, re
sys.path.insert(0, '.')
from core.data import questions, gold, history
from core.gold_turns import gold_turns
ASIDE = re.compile(r"\b(by the way|oh,? and|also,|speaking of|quick aside|before I forget|on a (?:different|related|separate|happier|brighter) note|completely unrelated|totally unrelated|random(?: \w+)? (?:note|news|update|thing)|update:|actually,)", re.I)
split = sys.argv[1] if len(sys.argv) > 1 else 'dev'
G = gold(split); GT = gold_turns()
qs = [q for q in questions(split) if G.get(q.question_id, {}).get('question_type') == 'single-session-user' and not G[q.question_id]['abstain']]
g_n = g_a = all_n = all_a = 0
for q in qs:
    h = history(split, q.history_id)
    gt = set(GT.get(q.question_id, []))
    for s in h['sessions']:
        for t in s['turns']:
            if t['role'] != 'user':
                continue
            a = bool(ASIDE.search(t['content']))
            all_n += 1; all_a += a
            if t['turn_id'] in gt:
                g_n += 1; g_a += a
print(f"{split}: gold user turns with aside cue {g_a}/{g_n} = {g_a/g_n:.2f}; all user turns {all_a}/{all_n} = {all_a/all_n:.3f}")
