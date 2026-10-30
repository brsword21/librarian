"""Exact-term presence as an abstention signal on dev temporal: proper nouns / quoted titles / rare content words of the
question that never appear in the history."""
import json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from core.data import gold, questions, history  # noqa

STOP = set("""a an the and or of to in at for on with by from about into my me i we our you your his her their it its this that
which what when how many much did do does was were is are be been had have has after before since between first last
day days week weeks month months year years ago passed long take took event events happened order three two""".split())


def key_terms(q):
    terms = set()
    for m in re.finditer(r"'([^']{3,})'|\"([^\"]{3,})\"", q):
        terms.add((m.group(1) or m.group(2)).lower())
    toks = re.findall(r"[A-Za-z][A-Za-z0-9'\-]+", q)
    for i, t in enumerate(toks):
        if i > 0 and t[0].isupper() and t.lower() not in STOP and t != "I":
            terms.add(t.lower().rstrip("'s").rstrip("'"))
    return terms


for split in ("dev", "dev200"):
    g = gold(split)
    qs = [q for q in questions(split) if g[q.question_id]["question_type"] == "temporal-reasoning"]
    c = Counter()
    for q in qs:
        h = history(split, q.history_id)
        text = " ".join(t["content"] for s in h["sessions"] for t in s["turns"]).lower()
        terms = key_terms(q.question)
        miss = [t for t in terms if t not in text]
        ab = g[q.question_id]["abstain"]
        c[(ab, bool(miss))] += 1
        if ab or miss:
            print(split, "ABST" if ab else "ANS ", "miss=", miss, "|", q.question[:120])
    print(split, dict(c))
