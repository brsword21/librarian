"""S / Sall / PA / ALL / ATR / CF1 / passages on the whole-question subset (no parsed events, not gap) of a run."""
import json, re, sys
sys.path.insert(0, '.')
from lenses.temporal import b_evcal as E
_GAP = re.compile(r"how many (days|weeks|months)\b.*\b(apart|after|before|between|passed)|days? (apart|after|before)", re.I)
def sub(r, which):
    g = bool(_GAP.search(r['question']))
    if which == 'gap': return g
    if g: return False
    ev = bool(E.parse_question(r['question'])['events'])
    return (not ev) if which == 'other' else ev
for p in sys.argv[1:]:
    rows = [json.loads(l) for l in open(p + '/per_question.jsonl')]
    for which in ['gap', 'event', 'other']:
        v = [r for r in rows if sub(r, which) and not r['abstain_gold']]
        n = len(v) or 1
        m = lambda k: sum((x.get(k) or 0) for x in v) / n
        print(f"{p.split('temporal/')[-1]:40s} {which:6s} n={len(v):3d} S {m('S'):.1f} Sall {m('Sall'):.1f} PA {m('PA'):.3f} ALL {m('ALL'):.3f} ATR {m('ATR'):.3f} CF1 {m('CF1'):.3f} CF1all {m('CF1all'):.3f} np {sum(len(x['passages']) for x in v)/n:.1f} chars {m('chars'):.0f}")
