"""R4 probe: in-session candidate sentences for the quote fallback, scored by CE(question), CE(kind+purpose), dense."""
import json, sys
from core.index import HistoryIndex
from lenses.ssa import a_recsent as A

split, packs = sys.argv[1], sys.argv[2]
qids = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
for l in open(packs):
    r = json.loads(l)
    if r["route"] != "ssa" or (qids and r["question_id"] not in qids):
        continue
    hx = HistoryIndex.load(split, r["history_id"])
    qp = A.parse_question(r["question"])
    qp["cue_floor"] = 0.7
    idf = A.history_idf(hx)
    sid = r["cite_plan"][0]
    cands = []
    for t in hx.sess_by_id[sid]["turns"]:
        if t["role"] != "assistant":
            continue
        for s in A.sentences(t["content"]):
            sc, f = A.sent_struct(s, qp, idf)
            if f["ent"]:
                cands.append((s, sc, f))
    phrase = " ".join(x for x in (qp.get("kind"), qp.get("purpose")) if x)
    ce_q = hx.rerank_texts(r["question"], [c[0] for c in cands])
    ce_p = hx.rerank_texts(phrase, [c[0] for c in cands])
    dn = hx.dense_texts(phrase, [c[0] for c in cands])
    print(f"== {r['question_id']} {r['question']}  | phrase={phrase!r}")
    for (s, sc, f), a, b, c in sorted(zip(cands, ce_q, ce_p, dn), key=lambda x: -x[1]):
        print(f"   ceq {a:6.2f} cep {b:6.2f} dn {c:.3f} st {sc:.2f} cue {f['cue']} kind {int(f['kind'])} {s[:110]}")
