"""Smoke-run b_evcal.build() with a stub HistoryIndex (lexical scores only, no model server)."""
import json, sys
sys.path.insert(0, ".")
import core.paths  # noqa: F401  (adds the kit to sys.path)
from core.data import parse_date
from core.types import Question
from core.units import build_units
from lenses.temporal import b_evcal as L

class Stub:
    def __init__(self, split, hid):
        self.split, self.history_id = split, hid
        self.units, self.sessions = build_units(json.load(open(f"cache/hist/{split}/{hid}.json")))
        self.sess_by_id = {s["session_id"]: s for s in self.sessions}
    def neighbors(self, uid, before=1, after=1):
        u = self.units[uid]
        return [j for j in range(max(0, uid - before), min(len(self.units), uid + after + 1)) if self.units[j].session_id == u.session_id]
    def _ov(self, q, i):
        t = L.content_tokens(q); return len(t & L.content_tokens(self.units[i].text)) / max(1, len(t))
    def hybrid(self, query, k=100, uids=None, **kw):
        pool = uids if uids is not None else range(len(self.units))
        return sorted(((i, self._ov(query, i)) for i in pool), key=lambda x: -x[1])[:k]
    def rerank(self, query, uids):
        return sorted(((i, 10 * self._ov(query, i) - 5) for i in uids), key=lambda x: -x[1])

for line in open("../data/test/questions.jsonl"):
    r = json.loads(line)
    if r["history_id"] != "h_3c02cbc43fc9" or "days after" not in r["question"]:
        continue
    q = Question("x", r["history_id"], r["question"], parse_date(r["question_date"]), r["question_date"])
    pk = L.build(q, Stub("test", r["history_id"]), **L.VARIANTS["evcal"])
    print(f"{r['question'][:70]:70} computed={pk.computed} abst={pk.abstain_p} cite={pk.cite_plan} np={len(pk.passages)}")
print("HINT:", pk.hint)
