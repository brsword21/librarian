"""Qualitative test audit for lens A: question -> best sentence, margin, abstain_p, packed sessions, other cue sentences.
Usage: .venv/bin/python -m lenses.ssa.scratch_a.audit_best <variant> [n]   (test split, router == ssa; no gold)"""
import sys

from core.data import questions
from core.index import HistoryIndex
from core.router import route
from harness.sweep import load_lens

lens = load_lens("lenses/ssa/a_recsent.py")
variant = sys.argv[1] if len(sys.argv) > 1 else "rec_bm25"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 99
qs = [q for q in questions("test") if route(q.question)[0] == "ssa"][:n]
for q in qs:
    hx = HistoryIndex.load("test", q.history_id)
    pack = lens.build(q, hx, _variant=variant, **lens.VARIANTS[variant])
    b = pack.debug.get("best", {})
    print("=" * 110)
    print(f"Q: {q.question}")
    print(f"   qp={pack.debug.get('qp')} abst={pack.abstain_p} cite={pack.cite_plan} sess={pack.session_ids()} "
          f"chars={pack.debug.get('chars')}")
    print(f"   BEST[{b.get('margin')} conf={b.get('confident')}] {b.get('sentence', '')[:240]!r}")
    print(f"   feat={b.get('feat')}")
    if pack.computed:
        print(f"   COMPUTED: {pack.computed}")
    # other first-person recommendation sentences anywhere in the history (to see decoys / alternatives)
    qp = lens.parse_question(q.question)
    idf = lens.history_idf(hx)
    sc = []
    for u in hx.units:
        if u.role != "assistant":
            continue
        for s in lens.sentences(u.text):
            if lens.CUE_STRONG.search(s) or lens.CUE_MED.search(s):
                v, f = lens.sent_struct(s, qp, idf)
                if v > 0:
                    sc.append((v, u.session_id, s))
    sc.sort(key=lambda x: -x[0])
    for v, sid, s in sc[1:4]:
        print(f"     alt {v:.2f} {sid} {s[:160]!r}")
