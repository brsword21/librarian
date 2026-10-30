import json, sys
rows=[json.loads(l) for l in open('runs/samples/multi.jsonl')]
for r in rows:
    if r['split']!='dev': continue
    print('='*100)
    print(r['question_id'], '|', r['question'], '| date', r['question_date'], '| ans:', r['answer'], '| abst', r['abstain'], '| nsess', r['n_sessions_in_history'])
    print('  evidence:', [(e['session_id'][-6:], e['date'][:10]) for e in r['evidence']])
    for g in r['gold_turns']:
        t = g['text'].replace('\n',' ')
        print(f"  [{g['session_id'][-6:]} {g['date'][:10]} {g['role']}] {t[:400]}")
print('#'*100)
for r in rows:
    if r['split']=='test':
        print(r['question_id'], r.get('history_id',''), '|', r['question'], '|', r['question_date'])
