"""Precision of 'capitalized (non-initial) question token absent from user turns / from all turns' as abstain signal, all types."""
import re, sys
sys.path.insert(0, '.')
from core.data import gold, questions, history
SKIP = {"I", "I'm", "I've", "I'd", "Dr", "Mr", "Mrs", "Ms"}
def caps(q):
    toks = re.findall(r"[A-Za-zÀ-ÿø'’\-]+", q)
    return [t.strip("'’").removesuffix("'s").removesuffix("’s") for i, t in enumerate(toks)
            if i > 0 and t[0].isupper() and t not in SKIP and len(t) > 2]
for split in ("dev", "dev200"):
    g = gold(split); qs = {q.question_id: q for q in questions(split)}
    tab = {}
    for qid, x in g.items():
        q = qs[qid]; c = caps(q.question)
        if not c: continue
        h = history(split, q.history_id)
        ut = " ".join(t['content'] for s in h['sessions'] for t in s['turns'] if t['role'] == 'user').lower()
        at = " ".join(t['content'] for s in h['sessions'] for t in s['turns']).lower()
        mu = [w for w in c if w.lower() not in ut]; ma = [w for w in c if w.lower() not in at]
        for key, m in (("user", mu), ("all", ma)):
            k = (key, x['abstain'], bool(m)); tab[k] = tab.get(k, 0) + 1
        if mu and not x['abstain']:
            print(split, 'answerable flagged', x['question_type'], q.question[:80], mu, '(absent from all too)' if ma else '')
    print(split, sorted(tab.items()))
