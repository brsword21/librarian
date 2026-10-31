"""R4 scratch: sentence-level role features for nf0 ssu/multi-routed questions (dev, dev200, test)."""
import json, re, sys
sys.path.insert(0, '.')
from core.index import HistoryIndex
from core.types import Question
from harness.sweep import load_lens

FIRST = re.compile(r"\b(I|my|me|mine|I'm|I've|I'd|I'll|myself|our|ours|us|we|we're|we've)\b", re.I)
SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
br = load_lens('lenses/ssa/b_role.py')


def sents(t):
    return [s.strip() for s in SPLIT.split(t) if len(s.strip()) > 15]


def feats(q, hx, n=40):
    cand = hx.hybrid(q.question, k=100, pool=300)
    rr = hx.rerank(q.question, [u for u, _ in cand[:n]])
    by = {'user': [], 'assistant': []}
    for u, s in sorted(rr, key=lambda x: -x[1]):
        r = hx.units[u].role
        if len(by[r]) < 5:
            by[r].append((u, s))
    out = {}
    for role in ('user', 'assistant'):
        ss = []
        for u, _ in by[role]:
            for s in sents(hx.units[u].text):
                ss.append((u, s))
        if not ss:
            out[role] = (-20, '', 0, None)
            continue
        sc = hx.rerank_texts(q.question, [s for _, s in ss])
        i = max(range(len(ss)), key=lambda j: sc[j])
        out[role] = (sc[i], ss[i][1], len(FIRST.findall(ss[i][1])), ss[i][0])
    return out


def main(split):
    import json
    rows = [json.loads(l) for l in open(f'lenses/ssa/scratch_a/r3/role_feats_{split}.jsonl')]
    from core.data import questions
    qs = {q.question_id: q for q in questions(split)}
    res = []
    for r in rows:
        if r['route'] not in ('ssu', 'multi') or r['n_first'] != 0:
            continue
        q = qs[r['qid']]
        hx = HistoryIndex.load(split, q.history_id)
        f = feats(q, hx)
        row = dict(qid=r['qid'], q=r['q'], route=r['route'], gold=r.get('gold'), d=r['d'],
                   cs_a=f['assistant'][0], cs_u=f['user'][0], u_first=f['user'][2],
                   u_sent=f['user'][1][:160], a_sent=f['assistant'][1][:160])
        row['d_sent'] = row['cs_a'] - row['cs_u']
        res.append(row)
        print(split, row['route'], (row['gold'] or '')[:14], 'd=%.2f ds=%.2f uf=%d' % (row['d'], row['d_sent'], row['u_first']),
              row['q'][:70], '|U:', row['u_sent'][:90])
    with open(f'lenses/ssa/scratch_a/r4/sent_feats_{split}.jsonl', 'w') as fh:
        for row in res:
            fh.write(json.dumps(row) + '\n')


if __name__ == '__main__':
    main(sys.argv[1])
