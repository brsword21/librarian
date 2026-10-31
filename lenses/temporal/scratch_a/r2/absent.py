import re
from core.index import HistoryIndex
from core.data import questions, gold
from lenses.temporal import a_calendar as A
GAP = re.compile(r"how many (days|weeks|months)\b.*\b(apart|after|before|between|passed)|days? (apart|after|before)", re.I)
for split in ["dev", "dev200", "test"]:
    g = gold(split) if split != "test" else {}
    for q in questions(split):
        if g and g[q.question_id]["question_type"] != "temporal-reasoning": continue
        if not GAP.search(q.question): continue
        hx = HistoryIndex.load(split, q.history_id)
        c = A._hxc(hx)
        qp = A.parse_question(q.question)
        miss = []
        for ev in qp.events:
            for t, _ in A.toks(re.sub(r"\([^)]*\)", " ", ev)):
                if c.df.get(t, 0) == 0: miss.append(t)
        ab = g[q.question_id]["abstain"] if g else "?"
        if miss or ab is True:
            print(split, "ABST" if ab is True else "    ", miss, "|", q.question[:110])
