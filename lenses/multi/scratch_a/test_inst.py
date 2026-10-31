"""For a test question (substring), list sessions with an A-lexical instance sentence: strength, window, in pack."""
import sys, json
from core.data import questions
from core.index import HistoryIndex
from lenses.multi import b_sweep as B, a_tally as T, a_prune as AP

sub = sys.argv[1]
variant = sys.argv[2] if len(sys.argv) > 2 else "p8x1"
q = next(q for q in questions("test") if sub.lower() in q.question.lower())
hx = HistoryIndex.load("test", q.history_id)
P = dict(B.VARIANTS["sweep"]); P.update(AP.VARIANTS[variant])
a = B.analyze(q.question, q.date)
ranked, final, rr, lab, facet_top, rest, win_active = B._score_units(q, hx, a, P)
st = AP._sess_strength(hx, rr, a, win_active, P)
pack = AP.build(q, hx, **P)
inpack = {p.id for p in pack.passages}
qa = T.analyze(q.question, q.date)
print(q.question, "| window", a["window"], "active", win_active)
for s in hx.sessions:
    best = (0, "")
    for t in s["turns"]:
        if t["role"] != "user":
            continue
        for se in T.sentences(t["content"]):
            m = T.match_score(se, qa)
            if m > best[0]:
                best = (m, se)
    if best[0] >= 1.0:
        inw = a["window"] and a["window"]["start"] <= s["date"].date() <= a["window"]["end"]
        print(f"{'P' if s['session_id'] in inpack else ' '} {'W' if inw else ' '} {s['date_str'][:10]} st={st.get(s['session_id'], -99):6.2f} lex={best[0]:.1f} {T.cue_flags(best[1])} {best[1][:110]}")
