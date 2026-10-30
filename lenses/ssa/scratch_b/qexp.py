"""Compare SSA query/unit variants with a pure-python BM25 (relative numbers only)."""
import json, re, sys
from collections import defaultdict
sys.path.insert(0, '.'); sys.path.insert(0, 'lenses/ssa/scratch_b')
from minibm25 import Units, BM25, toks, ssa_questions
from core.data import history
sys.path.insert(0, 'lenses/ssa')
from b_semantic import clean_question, split_topic, declarative  # lens helpers (pure python)

GT = json.load(open('cache/gold_turns.json'))
def norm(s): return re.sub(r'\W+', ' ', s.lower()).strip()

def run(split, variant):
    res = []
    for q, g in ssa_questions(split):
        U = Units(history(split, q.history_id)); us = U.units
        gts = set(GT.get(q.question_id, [])); gsid = g['evidence'][0]
        ans = norm(g['answer'])
        idx_text = [(u['ctx'] + ' ' + u['text']) for u in us]
        bm = BM25([toks(t) for t in idx_text])
        cq = clean_question(q.question); topic, detail = split_topic(q.question)
        if variant == 'raw':
            sc = bm.score(toks(q.question))
        elif variant == 'clean':
            sc = bm.score(toks(cq))
        elif variant == 'clean_asst':
            sc = bm.score(toks(cq)); sc = [s if u['role'] == 'assistant' else s * 0.6 for s, u in zip(sc, us)]
        elif variant == 'decl':
            sc = bm.score(toks(cq + ' ' + declarative(q.question)))
        elif variant in ('round', 'round_topic'):
            sc = bm.score(toks(cq))
            # round aggregation: assistant unit gets + w * best score of the preceding user turn (same session)
            best_user = {}
            for i, u in enumerate(us):
                if u['role'] == 'user': best_user[(u['sid'], u['ti'])] = max(best_user.get((u['sid'], u['ti']), 0), sc[i])
            if variant == 'round_topic' and topic:
                ts = bm.score(toks(topic))
                sess_topic = defaultdict(float)
                for i, u in enumerate(us): sess_topic[u['sid']] = max(sess_topic[u['sid']], ts[i])
            sc2 = []
            for i, u in enumerate(us):
                s = sc[i]
                if u['role'] == 'assistant':
                    s += 0.4 * best_user.get((u['sid'], u['ti'] - 1), 0)
                if variant == 'round_topic' and topic:
                    s += 0.3 * sess_topic[u['sid']]
                sc2.append(s)
            sc = sc2
        order = sorted(range(len(us)), key=lambda i: -sc[i])
        # session ranking by max unit
        seen = []; 
        for i in order:
            if us[i]['sid'] not in seen: seen.append(us[i]['sid'])
        srank = seen.index(gsid) + 1
        trank = next((r + 1 for r, i in enumerate(order) if us[i]['tid'] in gts), 999)
        arank = next((r + 1 for r, i in enumerate(order) if ans and ans in norm(us[i]['text'])), None)
        res.append((srank, trank, arank, q.question_id))
    n = len(res)
    s1 = sum(r[0] == 1 for r in res) / n; s3 = sum(r[0] <= 3 for r in res) / n
    t1 = sum(r[1] == 1 for r in res) / n; t5 = sum(r[1] <= 5 for r in res) / n; t10 = sum(r[1] <= 10 for r in res) / n
    ar = [r[2] for r in res if r[2] is not None]
    a5 = sum(a <= 5 for a in ar) / max(1, len(ar)); a10 = sum(a <= 10 for a in ar) / max(1, len(ar))
    print(f'{split:6s} {variant:12s} n={n} sess@1={s1:.2f} sess@3={s3:.2f} turn@1={t1:.2f} turn@5={t5:.2f} turn@10={t10:.2f} ans_unit@5={a5:.2f} @10={a10:.2f} (n_ext={len(ar)})')
    return res

if __name__ == '__main__':
    for sp in sys.argv[1].split(','):
        for v in sys.argv[2].split(','):
            run(sp, v)
