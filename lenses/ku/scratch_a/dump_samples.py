import json, sys
for l in open('runs/samples/ku.jsonl'):
    d = json.loads(l)
    print('=====', d['split'], d.get('question_id'), d['question_date'], '| abstain', d.get('abstain'), '| nsess', d.get('n_sessions_in_history'))
    print('Q:', d['question'])
    if d['split'] != 'test':
        print('A:', d.get('answer'), '| ev:', [(e['session_id'], e['date']) for e in d.get('evidence') or []])
        for t in d.get('gold_turns') or []:
            print('   GT', t['session_id'], t['date'], t['role'], '|', t['text'][:260].replace('\n', ' '))
