"""Abstention signal: which question terms / bigrams never appear in the history (user turns / all turns)."""
import re, sys
sys.path.insert(0, '.')
from core.data import gold, questions, history
import Stemmer
st = Stemmer.Stemmer('english')
STOP = set("""a an the of in on at to for from with by about as and or but if is are was were be been being do does did
have has had i me my mine we our us you your what which who whom whose when where why how many much long often
time times currently current now these days right recently most recent so far still previous previously initially
before after since that this there their they them it its am can could would should will just any some other
first last get got go going total number""".split())
def toks(s):
    return re.findall(r"[A-Za-z][A-Za-z'\-]*|\d+", s)
def content(q):
    out = []
    for t in toks(q):
        tl = t.lower().strip("'")
        if tl.endswith("'s"): tl = tl[:-2]
        if tl in STOP or len(tl) < 3: continue
        out.append(tl)
    return out
split = sys.argv[1] if len(sys.argv) > 1 else 'dev'
types = sys.argv[2].split(',') if len(sys.argv) > 2 else ['knowledge-update']
g = gold(split); qs = {q.question_id: q for q in questions(split)}
stats = {True: [], False: []}
for qid, x in g.items():
    if x['question_type'] not in types: continue
    q = qs[qid]; h = history(split, q.history_id)
    utext = " ".join(t['content'] for s in h['sessions'] for t in s['turns'] if t['role'] == 'user')
    atext = " ".join(t['content'] for s in h['sessions'] for t in s['turns'])
    ustems = set(st.stemWords([w.lower() for w in toks(utext)]))
    astems = set(st.stemWords([w.lower() for w in toks(atext)]))
    c = content(q.question)
    cs = st.stemWords(c)
    miss_u = [w for w, s in zip(c, cs) if s not in ustems]
    miss_a = [w for w, s in zip(c, cs) if s not in astems]
    # bigram presence (adjacent content words) in user text, stem level
    ut = st.stemWords([w.lower() for w in toks(utext)])
    ubig = set(zip(ut, ut[1:]))
    qt = st.stemWords([w.lower().strip("'") for w in toks(q.question)])
    qbig = [(a, b) for a, b in zip(qt, qt[1:]) if a not in STOP and b not in STOP and len(a) > 2 and len(b) > 2]
    miss_big = [f"{a} {b}" for a, b in qbig if (a, b) not in ubig]
    stats[x['abstain']].append((bool(miss_u), bool(miss_a), bool(miss_big)))
    if x['abstain'] or miss_u or miss_big:
        print(('ABST ' if x['abstain'] else 'ans  ') + qid, '|', q.question[:90], '| miss_user:', miss_u, '| miss_all:', miss_a, '| miss_bigram:', miss_big)
for k, v in stats.items():
    n = len(v)
    print('abstain' if k else 'answerable', n, 'miss_user', sum(a for a, _, _ in v), 'miss_all', sum(b for _, b, _ in v), 'miss_bigram', sum(c for _, _, c in v))
