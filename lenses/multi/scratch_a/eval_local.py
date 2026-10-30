"""Local approximation of harness metrics for the a_tally lens (until harness.sweep lands).
usage: eval_local.py split variant [extra k=v ...]"""
import sys, json, statistics as st, time
from core.data import questions, gold
from core.gold_turns import gold_turns
from core.index import HistoryIndex
from lenses.multi import a_tally as L
split, var = sys.argv[1], sys.argv[2]
extra = {k: (int(v) if v.isdigit() else v) for k, v in (a.split("=") for a in sys.argv[3:])}
g, gt = gold(split), gold_turns()
rows = []; t0 = time.time(); abst = []
for q in questions(split):
    gg = g.get(q.question_id)
    if not gg or gg["question_type"] != "multi-session":
        continue
    hx = HistoryIndex.load(split, q.history_id)
    pk = L.build(q, hx, _variant=var, **{**L.VARIANTS[var], **extra})
    chars = L.message_chars(q.question, pk.hint, pk.passages)
    abst.append((pk.abstain_p, gg["abstain"], q.question, pk.debug["abstain_why"]))
    if gg["abstain"]:
        continue
    G, P = set(gg["evidence"]), set(pk.session_ids())
    A = set(gt.get(q.question_id, []))
    ALL = G <= P; ATR = len(A & pk.included_turns) / len(A) if A else 1.0
    C = set(pk.planned_citations()); tp = len(C & G)
    cf1 = 2 * tp / (len(C) + len(G)) if C else 0.0
    PA = ALL and ATR == 1.0
    rows.append(dict(qid=q.question_id, q=q.question, ALL=ALL, ATR=ATR, PA=PA, SR=len(G & P) / len(G), CF1=cf1,
                     chars=chars, np=len(P), win=pk.debug["window"], wu=pk.debug["window_used"]))
n = len(rows)
m = lambda k: sum(r[k] for r in rows) / n
S = 100 * sum(0.65 * r["PA"] + 0.30 * r["CF1"] - 0.05 * r["chars"] / 16000 for r in rows) / n
print(f"{split} {var} {extra} n={n} S={S:.1f} PA={m('PA'):.3f} ALL={m('ALL'):.3f} ATR={m('ATR'):.3f} SR={m('SR'):.3f} "
      f"CF1={m('CF1'):.3f} chars={st.mean(r['chars'] for r in rows):.0f} sess={st.mean(r['np'] for r in rows):.1f} "
      f"win_used={sum(r['wu'] for r in rows)} t={time.time()-t0:.0f}s")
# abstention AUC
pos = [a for a, ab, *_ in abst if ab]; neg = [a for a, ab, *_ in abst if not ab]
if pos and neg:
    auc = sum((p > n_) + 0.5 * (p == n_) for p in pos for n_ in neg) / (len(pos) * len(neg))
    print(f"abstain AUC={auc:.3f} (pos={len(pos)}) answerable with p>=0.5: {sum(x >= .5 for x in neg)}/{len(neg)}")
    for a, ab, qq, why in sorted(abst, key=lambda x: -x[0])[:20]:
        print(f"   {a:.2f} {'ABS' if ab else '   '} {qq[:80]} {why}")
json.dump(rows, open(f"lenses/multi/scratch_a/eval_{split}_{var}.json", "w"), indent=0)
