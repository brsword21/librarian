"""Qualitative look at test KU-style questions: grep sentences with key terms in the history (no gold)."""
import json, re, sys
sys.path.insert(0, '.')
from core.data import history
terms_by_q = {
 "ceramics class instructor": ["ceramic", "instructor", "teacher"],
 "accountant": ["accountant", "tax"],
 "job title": ["title", "promot", "role"],
 "watercolour": ["watercolo", "teaches", "instructor", "teacher"],
 "gigabytes": ["GB", "gigabyte", "data plan"],
 "monthly rent": ["rent"],
 "laps": ["laps"],
 "cups of coffee": ["cups of coffee", "cup of coffee", "coffee each"],
 "kilometers": ["kilomet", " km"],
 "Moroccan spices": ["Moroccan", "spice"],
 "UX team": ["UX team", "my team", "designers"],
 "skateboard": ["skateboard"],
 "long run": ["long run"],
 "Icelandic horses": ["Icelandic", "horse"],
 "chapters": ["chapter"],
}
for l in open('runs/samples/ku.jsonl'):
    d = json.loads(l)
    if d['split'] != 'test':
        continue
    key = next((k for k in terms_by_q if k.lower() in d['question'].lower()), None)
    if not key: continue
    h = history('test', d['history_id'])
    print('#####', d['question'], d['question_date'], d['history_id'], len(h['sessions']))
    pat = re.compile('|'.join(re.escape(t) for t in terms_by_q[key]), re.I)
    n = 0
    for si, s in enumerate(h['sessions']):
        for ti, t in enumerate(s['turns']):
            for sent in re.split(r'(?<=[.!?])\s+', t['content']):
                if pat.search(sent) and (t['role'] == 'user' or len(sent) < 250):
                    n += 1
                    if n <= 40:
                        print(f"  [{si}] {s['date'][:10]} {t['role'][0]} t{ti}: {sent[:260]}")
    print('  matches:', n)
