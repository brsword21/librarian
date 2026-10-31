import json, sys
r = {json.loads(l)['question_id']: json.loads(l) for l in open(sys.argv[2] if len(sys.argv) > 2 else 'runs/final/v2_test_packs.jsonl')}
for qid in sys.argv[1].split(','):
    x = r[qid]
    print('=' * 20, qid, x['route'], 'cite', x['cite_plan'], 'chars', x['chars'])
    print(x['question'][:900])
    for p in x['passages']:
        print('--', p['id'], p.get('date'))
        for line in p['text'].split('\n'):
            if line.startswith('user:'):
                print('   ', line[:400])
            else:
                print('    A:', line[6:120])
