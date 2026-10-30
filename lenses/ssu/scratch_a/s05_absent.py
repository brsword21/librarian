"""For each ssu question: which content words never appear in the history (user turns / any turn)? abstain signal check."""
import sys, re
sys.path.insert(0, '.')
from core.data import questions, gold, history
split = sys.argv[1] if len(sys.argv) > 1 else 'dev'
STOP = set("""a an the of to in on at for from with by about as into my me i i'm i've i'd we our us you your yours he she it they them
what which who whom whose where when why how is are was were be been being do does did done have has had having can could will would
should shall may might must that this these those there here and or but if so not no than then too very just also any some all many much
more most less few name named called type kind long time times day days often usually currently current now still last first new old
get got go went take took make made use used own favorite favourite previous initially finally end up ended spend spent buy bought
mention mentioned tell told say said again ago recently lately been per every each around""".split())
def stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w
G = gold(split)
qs = [q for q in questions(split) if G.get(q.question_id, {}).get('question_type') == 'single-session-user']
stats = {True: [0, 0], False: [0, 0]}
for q in qs:
    g = G[q.question_id]
    h = history(split, q.history_id)
    utext = " ".join(t['content'] for s in h['sessions'] for t in s['turns'] if t['role'] == 'user').lower()
    atext = " ".join(t['content'] for s in h['sessions'] for t in s['turns']).lower()
    ustems = {stem(w) for w in re.findall(r"[a-z0-9']+", utext)}
    astems = {stem(w) for w in re.findall(r"[a-z0-9']+", atext)}
    words = [w for w in re.findall(r"[a-z0-9']+", q.question.lower().replace("'s", "")) if w not in STOP and len(w) > 2]
    miss_u = [w for w in words if stem(w) not in ustems]
    miss_a = [w for w in words if stem(w) not in astems]
    stats[g['abstain']][0] += 1; stats[g['abstain']][1] += bool(miss_u)
    if miss_u or g['abstain']:
        print(f"abst={g['abstain']!s:5} miss_user={miss_u} miss_all={miss_a} | {q.question}")
print('abstain: n, flagged', stats[True], ' answerable: n, flagged', stats[False])
