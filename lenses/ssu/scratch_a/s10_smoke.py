"""Smoke-test build() with stub HistoryIndex / build_pack (lexical stand-ins) until core.index / core.pack land."""
import sys, types, importlib.util, re
sys.path.insert(0, '.')
from core.data import questions, gold, history
from core.units import build_units
from core.types import Passage

def stub_build_pack(q, hx, ranked, budget=12000, window=1, order="chrono", hint="", max_sessions=None, whole_turns=False):
    sess = []
    for uid in ranked:
        s = hx.units[uid].session_id
        if s not in sess: sess.append(s)
    sess = sess[: max_sessions or len(sess)]
    passages, inc, chars = [], set(), len(q.question) + len(hint)
    for s in sess:
        uids = sorted({n for uid in ranked if hx.units[uid].session_id == s
                       for n in range(max(0, uid - window), min(len(hx.units), uid + window + 1)) if hx.units[n].session_id == s})
        txt = "\n".join(f"{hx.units[n].role}: {hx.units[n].text}" for n in uids)
        if chars + len(txt) > budget and passages: break
        chars += len(txt); inc |= {hx.units[n].turn_id for n in uids}
        passages.append(Passage(id=s, date=hx.units[uids[0]].date_str, text=txt))
    return passages, inc, chars
pk = types.ModuleType("core.pack"); pk.build_pack = stub_build_pack; sys.modules["core.pack"] = pk

spec = importlib.util.spec_from_file_location("a_owner", "lenses/ssu/a_owner.py")
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)

class StubHX:
    def __init__(self, h):
        self.units, self.sessions = build_units(h)
    def _lex(self, query, roles):
        qs = {L.stem(w) for w in L.toks(query) if w not in L.STOP and len(w) > 2}
        out = [(u.uid, len(qs & {L.stem(w) for w in L.toks(u.index_text)})) for u in self.units if not roles or u.role in roles]
        return sorted(out, key=lambda x: -x[1])
    def hybrid(self, query, k=100, roles=None, **kw): return self._lex(query, roles)[:k]
    def bm25(self, query, k=200, roles=None): return self._lex(query, roles)[:k]
    def rerank(self, query, uids):
        d = dict(self._lex(query, None)); return [(u, d.get(u, 0) - 2.0) for u in uids]

split = sys.argv[1] if len(sys.argv) > 1 else 'dev'
G = gold(split)
qs = [q for q in questions(split) if G.get(q.question_id, {}).get('question_type') == 'single-session-user']
for vname, vp in L.VARIANTS.items():
    ok = cite_hit = 0; chars = []
    for q in qs[:40]:
        hx = StubHX(history(split, q.history_id))
        pack = L.build(q, hx, _variant=vname, **vp)
        ok += 1; chars.append(len(pack.hint))
        if not G[q.question_id]['abstain'] and pack.cite_plan and pack.cite_plan[0] in G[q.question_id]['evidence']:
            cite_hit += 1
    print(f"{vname:7s} built {ok} packs, cite@1 hit {cite_hit}, mean hint chars {sum(chars)/len(chars):.0f}")
print("example hint:", pack.hint[:400])
q = next(x for x in qs if 'sister' in x.question)
pk_ = L.build(q, StubHX(history(split, q.history_id)), _variant='notes', **L.VARIANTS['notes'])
print("notes hint:", pk_.hint[:600]); print("abstain_p", pk_.abstain_p, "computed", pk_.computed, "cite", pk_.cite_plan)
