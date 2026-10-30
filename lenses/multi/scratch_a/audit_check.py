"""Qualitative: for a test question (substring), grep the whole history's user turns for a regex and mark which hits
made it into the audit pack. Usage: audit_check.py <packs.jsonl> <question-substr> <regex>"""
import json, re, sys
from core.data import questions
from core.index import HistoryIndex
packs = {json.loads(l)['question_id']: json.loads(l) for l in open(sys.argv[1])}
qs = [q for q in questions('test') if sys.argv[2].lower() in q.question.lower()]
rx = re.compile(sys.argv[3], re.I)
for q in qs:
    pk = packs.get(q.question_id)
    if not pk: continue
    txt = '\n'.join(p['text'] for p in pk['passages'])
    ids = {p['id'] for p in pk['passages']}
    print(q.question, q.date_str, '| cite', len(pk.get('cite_plan') or []), '| sessions', len(ids), '| ap', pk.get('abstain_p'))
    print('HINT', pk['hint'][-260:])
    hx = HistoryIndex.load('test', q.history_id)
    for s in hx.sessions:
        for t in s['turns']:
            if t['role'] != 'user': continue
            for sent in re.split(r'(?<=[.!?])\s+', t['content']):
                if rx.search(sent):
                    inpack = sent[:60] in txt
                    cited = s['session_id'] in (pk.get('cite_plan') or [])
                    print(f"  {'IN ' if inpack else ('sess' if s['session_id'] in ids else '-- ')} {'C' if cited else ' '} {s['date_str'][:10]} {sent[:150]}")
