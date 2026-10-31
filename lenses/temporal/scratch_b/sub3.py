"""Per-subset metrics of a merged_r2-style run: group by the source route recorded in debug."""
import json, sys
from collections import defaultdict
sys.path.insert(0, '.')

def key(r):
    d = r.get('debug') or {}
    src = d.get('merged_r2_from') or d.get('r3_from') or ''
    if src.startswith('a_gap'):
        k = 'A:' + str((d.get('parse') or {}).get('kind'))
    else:
        k = 'B:' + str(d.get('route') or d.get('merged_from') or '?')
    return k

for p in sys.argv[1:]:
    rows = [json.loads(l) for l in open(p + '/per_question.jsonl')]
    groups = defaultdict(list)
    for r in rows:
        if r['abstain_gold']:
            continue
        groups[key(r)].append(r)
        groups['ALL'].append(r)
    print(p)
    for k, v in sorted(groups.items()):
        n = len(v)
        m = lambda f: sum((x.get(f) or 0) for x in v) / n
        print(f"  {k:28s} n={n:3d} S {m('S'):5.1f} Sall {m('Sall'):5.1f} PA {m('PA'):.3f} ALL {m('ALL'):.3f} ATR {m('ATR'):.3f} "
              f"CF1 {m('CF1'):.3f} CF1all {m('CF1all'):.3f} np {sum(len(x['passages']) for x in v)/n:4.1f} "
              f"ncite {sum(len(x.get('cite_plan') or []) for x in v)/n:3.1f} chars {m('chars'):5.0f}")
