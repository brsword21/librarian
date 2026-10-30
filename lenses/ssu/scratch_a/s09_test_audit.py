"""Qualitative audit on test (no gold, no tuning): top-5 user units by lexical proxy + structure for user-fact questions."""
import sys, importlib.util
from types import SimpleNamespace
sys.path.insert(0, '.')
from core.data import questions, history
from core.units import build_units
spec = importlib.util.spec_from_file_location("a_owner", "lenses/ssu/a_owner.py")
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
pick = [q for q in questions('test') if not L.ASK_ASSISTANT_RX.search(q.question)
        and not q.question.lower().startswith(('how many days', 'how many', 'how much'))]
for q in pick[: int(sys.argv[1]) if len(sys.argv) > 1 else 12]:
    units, _ = build_units(history('test', q.history_id))
    qp = L.parse_question(q.question)
    qst = {L.stem(w) for w in L.toks(q.question) if w not in L.STOP and len(w) > 2}
    lex = {u.uid: len(qst & {L.stem(w) for w in L.toks(u.index_text)}) / max(1, len(qst)) for u in units if u.role == 'user'}
    pool = sorted(lex, key=lambda x: -lex[x])[:120]
    cls = {uid: L.unit_class(units[uid], qp) for uid in pool}
    sc = {uid: (lex[uid] + L.struct_adjust(cls[uid], qp, L.DEFAULTS)[1]) * L.struct_adjust(cls[uid], qp, L.DEFAULTS)[0] for uid in pool}
    r = sorted(pool, key=lambda x: -sc[x])
    print(f"## {q.question}  [head={qp.head} chain={qp.chain} rec={int(qp.recency)}]")
    for uid in r[:5]:
        c = cls[uid]
        print(f"   {sc[uid]:.2f} {units[uid].date_str[:10]} {c.owner:8s} {c.polarity:5s} vals={c.values[:2]} | {L._snip(c.sent, 110)}")
