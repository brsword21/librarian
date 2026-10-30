"""Pure-python BM25 testbed approximating core units (sentence-aligned <=700-char chunks of a turn, ctx = last
sentence of previous turn). Only for comparing SSA query/granularity ideas before core lands."""
import json, math, re, sys
from collections import Counter, defaultdict
sys.path.insert(0, '.')
from core.data import questions, gold, history

STOP = set("""a an the and or but if of to in on at for from by with about as is are was were be been being do does did
have has had i me my mine you your yours we our us it its this that these those what which who whom whose when where why how
can could would should will shall may might must so than then there here just also very really any some all no not
remind tell""".split())

def stem(w):
    for suf in ('ing', 'edly', 'ed', 'es', 's', 'ly'):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    return w

def toks(s):
    return [stem(w) for w in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", s.lower()) if w not in STOP]

SENT = re.compile(r'(?<=[.!?])\s+|\n+')
def chunk(text, maxc=700):
    parts = [p for p in SENT.split(text) if p and p.strip()]
    out, cur = [], ''
    for p in parts:
        if cur and len(cur) + len(p) + 1 > maxc:
            out.append(cur); cur = p
        else:
            cur = (cur + ' ' + p).strip()
    if cur: out.append(cur)
    return out or [text]

def last_sentence(text):
    ps = [p for p in SENT.split(text) if p.strip()]
    return ps[-1][-200:] if ps else ''

class Units:
    def __init__(self, h):
        self.units = []
        for si, s in enumerate(h['sessions']):
            prev = ''
            for ti, t in enumerate(s['turns']):
                for ci, c in enumerate(chunk(t['content'])):
                    self.units.append(dict(sid=s['session_id'], si=si, tid=t['turn_id'], ti=ti, role=t['role'], ci=ci,
                                           text=c, ctx=(last_sentence(prev) if ci == 0 else ''), date=s['date']))
                prev = t['content']
        self.sess = h['sessions']

class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = [Counter(d) for d in docs]
        self.len = [len(d) for d in docs]
        self.avg = sum(self.len) / max(1, len(self.len))
        df = Counter()
        for d in self.docs: df.update(d.keys())
        N = len(docs)
        self.idf = {w: math.log(1 + (N - n + .5) / (n + .5)) for w, n in df.items()}
        self.k1, self.b = k1, b
    def score(self, q):
        out = []
        qc = Counter(q)
        for i, d in enumerate(self.docs):
            s = 0.0
            for w, qn in qc.items():
                f = d.get(w)
                if f:
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
            out.append(s)
        return out

def ssa_questions(split):
    g = gold(split)
    return [(q, g[q.question_id]) for q in questions(split) if g[q.question_id]['question_type'] == 'single-session-assistant']
