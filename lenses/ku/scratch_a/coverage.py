"""Abstention signal: IDF-weighted coverage of the question's content stems by the best single user turn (and window)."""
import math, re, sys
sys.path.insert(0, '.')
from core.data import gold, questions, history
import Stemmer
st = Stemmer.Stemmer('english')
STOPW = set("""a an the of in on at to for from with by about as and or but if is are was were be been being do does did
have has had i me my mine we our us you your what which who whom whose when where why how many much long often
time times currently current now these days right recently most recent so far still previous previously initially
before after since that this there their they them it its am can could would should will just any some other
first last get got go going total number new old ago""".split())
STOP = set(st.stemWords(list(STOPW))) | STOPW
def toks(s): return re.findall(r"[A-Za-z][A-Za-z'\-]*|\d+", s)
def stems(s): return [x for x in st.stemWords([w.lower().strip("'").removesuffix("'s") for w in toks(s)]) if x not in STOP and len(x) > 2]
split = sys.argv[1] if len(sys.argv) > 1 else 'dev'
types = sys.argv[2].split(',') if len(sys.argv) > 2 else ['knowledge-update']
g = gold(split); qs = {q.question_id: q for q in questions(split)}
res = {True: [], False: []}
for qid, x in g.items():
    if x['question_type'] not in types: continue
    q = qs[qid]; h = history(split, q.history_id)
    docs = [set(stems(t['content'])) for s in h['sessions'] for t in s['turns'] if t['role'] == 'user']
    N = len(docs)
    qst = list(dict.fromkeys(stems(q.question)))
    if not qst: continue
    df = {w: sum(w in d for d in docs) for w in qst}
    idf = {w: math.log((N + 1) / (df[w] + 0.5)) for w in qst}
    tot = sum(idf.values())
    best = max(sum(idf[w] for w in qst if w in d) / tot for d in docs)
    absent = [w for w in qst if df[w] == 0]
    res[x['abstain']].append((best, qid, absent))
for k in (True, False):
    v = sorted(res[k])
    print('ABSTAIN' if k else 'answerable', len(v), [f"{b:.2f}" for b, _, _ in v][:20])
# threshold sweep
for th in (0.6, 0.7, 0.75, 0.8, 0.85, 0.9):
    print(th, 'abst caught', sum(b < th for b, _, _ in res[True]), '/', len(res[True]), '| answerable flagged', sum(b < th for b, _, _ in res[False]), '/', len(res[False]))
