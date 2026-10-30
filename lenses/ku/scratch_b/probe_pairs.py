"""Debug the pair selection: top sessions with best sentence + score parts; '*' marks gold sessions (dev splits).
usage: probe_pairs.py <split> <variant> [n] [--miss]   (--miss: print only questions whose pair != gold)"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "lenses" / "ku"))
from core.data import gold, questions
from core.index import HistoryIndex
import b_semantic as L

split, var = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 999
only_miss = "--miss" in sys.argv
g = gold(split)
P = L.VARIANTS[var]
qs = [q for q in questions(split) if g.get(q.question_id, {}).get("question_type") == "knowledge-update"][:n]
hit = tot = 0
for q in qs:
    gg = g[q.question_id]
    hx = HistoryIndex.load(split, q.history_id)
    r = L.analyze(q, hx, **P)
    G = set(gg["evidence"])
    ok = set(r["pair"]) == G
    if not gg["abstain"]:
        tot += 1; hit += ok
    if only_miss and (ok or gg["abstain"]):
        continue
    print("=" * 6, q.question, "|", gg["answer"][:50], "| abstain" if gg["abstain"] else "", f"| ab_p={r['abstain_p']:.2f}",
          "| PAIR OK" if ok else "| PAIR MISS")
    for sid in r["sess_rank"][:6]:
        s = r["best_by_sess"][sid]
        mark = ("*" if sid in G else " ") + ("P" if sid in r["pair"] else " ")
        srr = f"{s['sent_rr']:6.2f}" if s.get("sent_rr") is not None else "   -  "
        print(f"  {mark} [{hx.sess_by_id[sid]['sess_idx']:3d}] sc={s['score']:6.2f} u={s['unit_rr']:6.2f} s={srr} "
              f"own={s['own']:+.1f} cov={s['cov']:.2f} v={int(s['val'])} | {s['raw'][:140]}")
    for sid in G - set(r["sess_rank"][:6]):
        rk = r["sess_rank"].index(sid) if sid in r["sess_rank"] else None
        print(f"  * gold session not in top6 (rank {rk})")
print(f"pair exact = {hit}/{tot}")
