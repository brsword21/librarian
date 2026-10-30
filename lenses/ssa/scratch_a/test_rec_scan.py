"""Qualitative: for each test 'you recommended' question, list assistant sentences carrying a recommendation cue
that share a content word with the question. Test = audit only, no tuning."""
import json, re, sys
STOP = set("what was the name of that you recommended recommend for my me i to in did which is a an use title".split())
CUE = re.compile(r"\b(i(?:'|’)?d recommend|i recommend|i recommended|i(?:'|’)?d suggest|i suggest|try|check out|go with|go for|"
                 r"worth|has a good|is great|is a great|good option|best bet|my pick|look into|consider)\b", re.I)
qs = [json.loads(l) for l in open('../data/test/questions.jsonl')]
for q in qs:
    t = q['question']
    if not re.search(r'you recommend', t, re.I):
        continue
    words = {w for w in re.findall(r"[a-z0-9\-\.]+", t.lower()) if w not in STOP and len(w) > 2}
    h = json.load(open(f"cache/hist/test/{q['history_id']}.json"))
    print("\n####", t, sorted(words))
    for si, s in enumerate(h['sessions']):
        for ti, tt in enumerate(s['turns']):
            if tt['role'] != 'assistant':
                continue
            for sent in re.split(r'(?<=[.!?])\s+', tt['content']):
                if CUE.search(sent):
                    sw = set(re.findall(r"[a-z0-9\-\.]+", sent.lower()))
                    ov = {w for w in words if any(x.startswith(w[:5]) for x in sw)}
                    if ov and len(tt['content']) < 700:
                        print(f"  [{si} t{ti} L{len(tt['content'])}] {sorted(ov)} :: {sent[:220]}")
