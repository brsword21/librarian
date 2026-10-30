"""Smoke-test build() with a stub core.pack (real one not landed yet). BM25-only variant, no model server."""
import sys, types
sys.path.insert(0, '.')
try:
    import core.pack  # noqa
except ImportError:
    from core.types import Passage
    stub = types.ModuleType("core.pack")
    def build_pack(q, hx, ranked, budget=12000, window=1, order="chrono", hint="", max_sessions=None, whole_turns=False):
        chosen, sess = [], []
        for u in ranked:
            sid = hx.units[u].session_id
            if sid not in sess:
                if max_sessions and len(sess) >= max_sessions: continue
                sess.append(sid)
            chosen += hx.neighbors(u, window, window)
            if sum(len(hx.units[i].text) for i in set(chosen)) > budget: break
        chosen = sorted(set(chosen))
        ps = [Passage(s, hx.sess_by_id[s]["date_str"], "\n".join(f"{hx.units[i].role}: {hx.units[i].text}" for i in chosen if hx.units[i].session_id == s)) for s in sorted(sess, key=lambda s: hx.sess_by_id[s]["sess_idx"])]
        return ps, {hx.units[i].turn_id for i in chosen}, sum(len(p.text) for p in ps) + len(hint)
    stub.build_pack = build_pack
    sys.modules["core.pack"] = stub
from core.data import gold, questions
from core.index import HistoryIndex
from lenses.ku import a_timeline as L
split = sys.argv[1] if len(sys.argv) > 1 else "dev"
g = gold(split); qs = {q.question_id: q for q in questions(split)}
ids = [qid for qid, x in g.items() if x["question_type"] == "knowledge-update"][:: max(1, int(sys.argv[2]) if len(sys.argv) > 2 else 9)]
for qid in ids:
    q = qs[qid]; hx = HistoryIndex.load(split, q.history_id)
    pk = L.build(q, hx, **{**L.VARIANTS["tl_bm25"], "_variant": "tl_bm25"})
    x = g[qid]
    print(f"--- {q.question} | gold={str(x['answer'])[:40]} abst={x['abstain']} | ap={pk.abstain_p} cite={pk.cite_plan} gold_ev={x['evidence']} computed={pk.computed} chars={pk.debug['chars']}")
    print("    HINT:", pk.hint.replace("\n", "\n          "))
