"""Debug one or more dev questions: picks (session, sentence, score) vs gold turns."""
import sys, json
from core.gold_turns import gold_turns
from core.index import HistoryIndex
from core.data import questions, gold
from harness.sweep import load_lens
lens = load_lens(sys.argv[1]); split = sys.argv[2]; variant = sys.argv[3]; qids = sys.argv[4:]
gt = gold_turns(); g = gold(split)
qs = {q.question_id: q for q in questions(split)}
for qid in qids:
    q = qs[qid]; hx = HistoryIndex.load(split, q.history_id)
    print('=' * 100); print(q.question, '| asked', q.date_str, '| gold:', g[qid]['answer'][:100])
    gold_s = set(g[qid]['evidence'])
    for t in gt.get(qid, []):
        us = hx.turn_units(t); u = hx.units[us[0]]
        print('  GOLD', u.session_id, u.date_str, u.role, 't%d' % u.turn_idx, ' '.join(hx.units[i].text for i in us)[:250])
    pack = lens.build(q, hx, _variant=variant, **lens.VARIANTS[variant])
    d = pack.debug
    print('  parse', d.get('parse'), 'computed', pack.computed, 'abst', pack.abstain_p)
    for p in d.get('picks', []): print('  PICK', p)
    for uid in d['ranking'][:8]:
        u = hx.units[uid]
        print('   rk', uid, u.session_id, 'G' if u.session_id in gold_s else '-', u.date_str[:10], u.role, 't%d' % u.turn_idx, u.text[:120].replace('\n', ' '))
    print('  HINT', pack.hint[:600])
    print('  pack sessions', [(p.id, 'G' if p.id in gold_s else '-') for p in pack.passages], 'cite', pack.cite_plan)
