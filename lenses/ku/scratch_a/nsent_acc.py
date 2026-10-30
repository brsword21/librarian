"""How often does the newest (or older, for 'previous' questions) mention sentence contain the gold answer?"""
import json, sys
sys.path.insert(0, '.')
import core.paths  # noqa
from score import answer_matched
from core.data import gold
run, split = sys.argv[1], sys.argv[2]
g = gold(split)
rows = [json.loads(l) for l in open(f'{run}/{split}/per_question.jsonl')]
n = ok = 0
for r in rows:
    if r.get('abstain_gold'): continue
    d = r.get('debug', {})
    sent = d.get('older_sent') if d.get('direction') == 'previous' else d.get('newest_sent')
    hit = bool(sent) and answer_matched(sent, g[r['question_id']])
    n += 1; ok += hit
    if not hit and '-v' in sys.argv:
        print(' MISS', d.get('direction'), r['question'][:70], '| gold', g[r['question_id']]['answer'][:30], '| sent', (sent or '')[:100])
print(f'{split}: answer in target sentence {ok}/{n}')
