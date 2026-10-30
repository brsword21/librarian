"""Qualitative: hints/timelines on test-style KU sample questions (BM25 variant, stub pack). No gold, no tuning."""
import json, sys
sys.path.insert(0, '.')
sys.argv = [sys.argv[0]]
exec(open('lenses/ku/scratch_a/smoke_build.py').read().split("from core.data import gold")[0])   # installs the stub
from core.data import parse_date
from core.types import Question
from core.index import HistoryIndex
from lenses.ku import a_timeline as L
for l in open('runs/samples/ku.jsonl'):
    d = json.loads(l)
    if d['split'] != 'test': continue
    q = Question("t", d['history_id'], d['question'], parse_date(d['question_date']), d['question_date'])
    hx = HistoryIndex.load('test', d['history_id'])
    pk = L.build(q, hx, **L.VARIANTS['tl_bm25'])
    print(f"--- {d['question']} | ap={pk.abstain_p} cite={[hx.sess_by_id[s]['sess_idx'] for s in (pk.cite_plan or [])]} computed={pk.computed}")
    for t in pk.debug['timeline'][-4:]: print('     TL', t)
    for t in pk.debug['other'][:2]: print('     OTHER', t)
