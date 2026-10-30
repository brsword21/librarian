"""Debug one KU question with a lens variant: mentions per session, pair, chosen units. Usage: dbg_q.py split variant qid..."""
import sys
sys.path.insert(0, '.')
from core.data import questions, gold
from core.index import HistoryIndex
from core.gold_turns import gold_turns
from harness.sweep import load_lens

split, var, qids = sys.argv[1], sys.argv[2], sys.argv[3:]
lens = load_lens('lenses/ku/a_timeline.py')
qs = {q.question_id: q for q in questions(split)}
g = gold(split); gt = gold_turns()
for qid in qids:
    q = qs[qid]; hx = HistoryIndex.load(split, q.history_id)
    p = {**lens.VARIANTS[var]}
    spec, ranking, mentions, tl, dbg = lens.analyse(q, hx, p)
    G = g[qid]['evidence']; A = set(gt.get(qid, []))
    print('=' * 100); print(q.question, '| gold:', g[qid]['answer'], '| key', spec.key, spec.atype, spec.direction)
    gold_uids = [i for t in A for i in hx.turn_units(t)]
    print('gold uids ranks:', [(u, ranking.index(u) if u in ranking else None) for u in gold_uids])
    for m in sorted(mentions, key=lambda m: m.sort_key):
        flag = ('G' if m.session_id in G else ' ') + ('T' if hx.units[m.uid].turn_id in A else ' ')
        print(f"  {flag} {m.date_str[:10]} {m.session_id} u{m.uid} {m.role[:4]} {m.owner:5s} sc={m.score:.2f} cov={m.cov:.2f} v={m.vals[:3]} | {m.sent[:110]}")
    print('newest', tl.newest and tl.newest.session_id, 'older', tl.older and tl.older.session_id, 'gold', G)
    pack = lens.build(q, hx, _variant=var, **p)
    print('cite', pack.cite_plan, 'passages', [(ps.id, len(ps.text)) for ps in pack.passages])
    print('HINT:', pack.hint[:600])
