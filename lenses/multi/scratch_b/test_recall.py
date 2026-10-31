"""Test audit helper (no gold): sessions whose user turns state a first-person fact with a question head term,
and whether the pack holds them.  .venv/bin/python -m lenses.multi.scratch_b.test_recall PACKS.jsonl"""
import json, re, sys
from core.data import questions
from core.index import HistoryIndex
from lenses.multi import b_sweep as R1
from lenses.multi.b_r3_full import split_sents, fact_score

packs = {json.loads(l)["question_id"]: json.loads(l) for l in open(sys.argv[1])}
qs = {q.question_id: q for q in questions("test")}
for qid, p in packs.items():
    q = qs[qid]
    hx = HistoryIndex.load("test", q.history_id)
    a = R1.analyze(q.question, q.date)
    keys = {R1._stem5(w) for w in a["terms"] if w not in R1._GENERIC}
    inpack = {x["id"] for x in p["passages"]}
    hits = {}
    for s in hx.sessions:
        for t in s["turns"]:
            if t["role"] != "user":
                continue
            for se in split_sents(t["content"]):
                toks = {R1._stem5(w) for w in re.findall(r"[a-z0-9][a-z0-9'\-]*", se.lower())}
                if keys & toks and fact_score(se) >= 1 and not R1._REPORT.search(se) and not R1._THIRD_SUBJ.search(se):
                    hits.setdefault(s["session_id"], se)
    miss = {k: v for k, v in hits.items() if k not in inpack}
    print(f"== {q.question[:80]} | pack {len(inpack)} cite {len(p['cite_plan'] or [])} | fact-hit sessions {len(hits)}, outside pack {len(miss)}")
    for k, v in list(miss.items())[:4]:
        print(f"     OUT {hx.sess_by_id[k]['date_str'][:10]} {v[:150]}")
