import json, sys, re
P = [json.loads(l) for l in open(sys.argv[1])]
want = set(sys.argv[2:])
for p in P:
    if p['route'] != 'temporal': continue
    if want and p['question_id'] not in want: continue
    print('=====', p['question_id'], 'comp=', p['computed'], 'ap=', p['abstain_p'], 'cite=', p['cite_plan'])
    print(p['question_text'])
    for ps in p['passages']:
        print('--', ps['id'], ps['date'])
        for line in ps['text'].split('\n'):
            if line.startswith('user:') or line.startswith('assistant:'):
                if line.startswith('user:') or re.search(r'\d', line):
                    print('   ', line[:400])
