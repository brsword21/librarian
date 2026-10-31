"""Strict pack check: does every gold turn's text survive sentence trimming? (ATR counts a turn even when trimmed.)
    .venv/bin/python -m lenses.multi.scratch_b.strict LENS VARIANT SPLIT [--show N]"""
import re, sys, json
from collections import Counter
from core.data import questions, gold
from core.gold_turns import gold_turns
from core.index import HistoryIndex
from harness.sweep import load_lens
from lenses.multi.b_sweep import split_sents, _FACT
_NUMW = re.compile(r"\b(\d|one|two|three|four|five|six|seven|eight|nine|ten|twelve|dozen|couple|half)\b", re.I)
isfact = lambda s: bool(_FACT.search(s) or _NUMW.search(s))

lens_path, variant, split = sys.argv[1:4]
gtype = sys.argv[sys.argv.index("--gtype") + 1] if "--gtype" in sys.argv else "multi-session"
show = int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 0
L = load_lens(lens_path)
g, gt = gold(split), gold_turns()
norm = lambda s: re.sub(r"\s+", " ", s).strip()
n = pa = pas = paf = 0
lostf = []
ch = 0
lost = []
for q in questions(split):
    gg = g[q.question_id]
    if gg["question_type"] != gtype or gg["abstain"]:
        continue
    hx = HistoryIndex.load(split, q.history_id)
    p = L.build(q, hx, _variant=variant, **L.VARIANTS[variant])
    text = norm(" ".join(x.text for x in p.passages))
    ch += len(text)
    G = set(gg["evidence"]); P = {x.id for x in p.passages}
    turns = gt.get(q.question_id, [])
    inc = set(p.included_turns or [])
    ok = G <= P and all(t in inc for t in turns)
    full = True; factok = True
    for t in turns:
        for u in hx.turn_units(t):
            un = hx.units[u]
            if un.role != "user":
                continue
            for s in split_sents(un.text):
                if norm(s) not in text:
                    full = False
                    if isfact(s):
                        factok = False
                        if ok:
                            lostf.append((q.question_id, q.question[:70], s[:160]))
                    if ok:
                        lost.append((q.question_id, q.question[:70], s[:160]))
    n += 1; pa += ok; pas += ok and full; paf += ok and factok
print(f"{lens_path} {variant} {split}: n={n} PA={pa/n:.3f} PA_strict={pas/n:.3f} PA_fact={paf/n:.3f} lost_fact_sents={len(lostf)} lost_sents={len(lost)} in {len({l[0] for l in lost})} q  passage_chars={ch/n:.0f}")
for l in lostf[:show]:
    print("  ", l[0], l[1], "|", l[2])
