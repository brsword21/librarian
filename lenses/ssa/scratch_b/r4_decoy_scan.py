"""R4 scan: for every ssa-routed test pack, list the assistant sentences (whole history) that best match the
question by cross-encoder, and flag packs whose chosen session is not the session of the best sentence.
Also counts sessions holding a recommendation sentence that shares the category noun (decoy candidates)."""
import json, re, sys
from core.index import HistoryIndex
sys.path.insert(0, ".")
from lenses.ssa.a_recsent import sentences, parse_question

split = sys.argv[1] if len(sys.argv) > 1 else "test"
packs = sys.argv[2] if len(sys.argv) > 2 else "runs/final/v2_test_packs.jsonl"
REC = re.compile(r"\b(recommend|suggest|you might like|you should|check out|try|consider|has a good|is great)\b", re.I)
for l in open(packs):
    r = json.loads(l)
    if r["route"] != "ssa":
        continue
    hx = HistoryIndex.load(split, r["history_id"])
    qp = parse_question(r["question"])
    sents = []
    for u in hx.units:
        if u.role != "assistant":
            continue
        for s in sentences(u.text):
            if REC.search(s):
                sents.append((u.session_id, s))
    if not sents:
        continue
    sc = hx.rerank_texts(r["question"], [s for _, s in sents])
    top = sorted(zip(sc, sents), key=lambda x: -x[0])[:4]
    chosen = set(r["cite_plan"] or [])
    flag = "" if top[0][1][0] in chosen else "  <<< TOP SENTENCE NOT IN PACK"
    print(f"== {r['question_id']} {r['question']}{flag}")
    for s, (sid, t) in top:
        mark = "*" if sid in chosen else " "
        print(f"   {mark} {s:6.2f} {sid} {t[:150]}")
