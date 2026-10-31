"""Run the gap analysis on test (or any split) gap questions: picks, scores, margins, conf. No gold used."""
import re, sys
from core.index import HistoryIndex
from core.data import questions
from harness.sweep import load_lens
GAP = re.compile(r"how many (days|weeks|months)\b.*\b(apart|after|before|between|passed)|days? (apart|after|before)", re.I)
lens = load_lens(sys.argv[1]); split = sys.argv[2]; variant = sys.argv[3]
only = sys.argv[4] if len(sys.argv) > 4 else None
P = lens.VARIANTS[variant]
for q in questions(split):
    if not GAP.search(q.question) or (only and only.lower() not in q.question.lower()):
        continue
    hx = HistoryIndex.load(split, q.history_id)
    pack = lens.build(q, hx, _variant=variant, **P)
    d = pack.debug
    print("=" * 110)
    print(q.date_str[:10], q.question)
    print(f"   computed={pack.computed} raw={d.get('computed_raw')} conf={d.get('conf')} abst={pack.abstain_p} np={len(pack.passages)} cite={pack.cite_plan and len(pack.cite_plan)} why={d.get('gate')}")
    for p in d.get("picks", []):
        print("     ", p)
    for line in (pack.hint or "").splitlines()[1:3]:
        print("      H:", line[:230])
