import json, sys
from core.index import HistoryIndex
from harness.sweep import load_lens
from core.types import Question
import inspect
L = load_lens('lenses/multi/a_r4_verb.py')
packs=[json.loads(l) for l in open('runs/final/v2_test_packs.jsonl')]
var = sys.argv[1] if len(sys.argv)>1 else 'vc'
from datetime import datetime
for p in packs:
    if p['route']!='multi': continue
    vre,w = L._verb_class(p['question_text'].split('\n')[0])
    hx=HistoryIndex.load('test', p['history_id'])
    qd = datetime.strptime(p['question_date'][:16], '%Y-%m-%d %H:%M') if '-' in p['question_date'] else None
    print(p['question_id'], '|', p['question_text'].split('\n')[0][:90], '| verb', w)
