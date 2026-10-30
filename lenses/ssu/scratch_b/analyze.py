"""Scratch: where do ssu gold turns sit and what makes them hard. Plain json + re only.

    .venv/bin/python lenses/ssu/scratch_b/analyze.py [dev|dev200]
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT.parent / "data"
split = sys.argv[1] if len(sys.argv) > 1 else "dev"

gt = json.loads((ROOT / "cache/gold_turns.json").read_text())
gold = {json.loads(l)["question_id"]: json.loads(l) for l in open(DATA / split / "gold.jsonl")}
qs = [json.loads(l) for l in open(DATA / split / "questions.jsonl")]

STOP = set("""a an the of to in on at for with my me i we our you your is are was were be been do did does what which who
whom where when how many much name names that this those these it its by from about as or and before after did i've i'm
have has had any some last first ever up end ended get got kind type""".split())


def words(s):
    return [w for w in re.findall(r"[a-z0-9']+", s.lower()) if w not in STOP and len(w) > 2]


def norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()


rows = []
for q in qs:
    g = gold[q["question_id"]]
    if g["question_type"] != "single-session-user":
        continue
    h = json.loads((ROOT / "cache/hist" / split / f"{q['history_id']}.json").read_text())
    sess = h["sessions"]
    tids = set(gt.get(q["question_id"], []))
    qw = set(words(q["question"]))
    # document frequency of question words across sessions (user turns only)
    df = Counter()
    for s in sess:
        utext = " ".join(t["content"] for t in s["turns"] if t["role"] == "user").lower()
        for w in qw:
            if re.search(r"\b" + re.escape(w[:max(4, len(w) - 2)]), utext):
                df[w] += 1
    info = dict(qid=q["question_id"], q=q["question"], ans=g["answer"], abst=g["abstain"], n=len(sess), df=dict(df))
    for si, s in enumerate(sess):
        for ti, t in enumerate(s["turns"]):
            if t["turn_id"] in tids:
                c = t["content"]
                a = g["answer"].lower()
                pos = c.lower().find(a.split(" (")[0][:25].lower())
                info.setdefault("turns", []).append(dict(sess_pos=round(si / len(sess), 2), role=t["role"], ti=ti,
                                                         nturns=len(s["turns"]), tlen=len(c), ans_pos=pos,
                                                         overlap=sorted(qw & set(words(c)))))
    rows.append(info)

print(f"{split}: {len(rows)} ssu questions, abstain {sum(r['abst'] for r in rows)}")
roles = Counter(t["role"] for r in rows for t in r.get("turns", []))
print("gold turn roles", roles)
print("gold turn index in session", Counter(t["ti"] for r in rows for t in r.get("turns", []) if t["role"] == "user"))
tl = sorted(t["tlen"] for r in rows for t in r.get("turns", []) if t["role"] == "user")
print("user gold turn len quartiles", tl[len(tl) // 4], tl[len(tl) // 2], tl[3 * len(tl) // 4], "max", tl[-1])
ap = [t["ans_pos"] for r in rows for t in r.get("turns", []) if t["role"] == "user"]
print("answer char pos in user turn: not found", sum(p < 0 for p in ap), "<200", sum(0 <= p < 200 for p in ap),
      "200-700", sum(200 <= p < 700 for p in ap), ">=700", sum(p >= 700 for p in ap))
print("n user gold turns per q", Counter(sum(t["role"] == "user" for t in r.get("turns", [])) for r in rows if not r["abst"]))
print("sess position", sorted(t["sess_pos"] for r in rows for t in r.get("turns", []) if t["role"] == "user"))
print()
for r in rows:
    ut = [t for t in r.get("turns", []) if t["role"] == "user"]
    print(f"{r['q'][:70]:70s} | {r['ans'][:30]:30s} | df={r['df']} | ov={[t['overlap'] for t in ut]} "
          f"ti={[t['ti'] for t in ut]} pos={[t['ans_pos'] for t in ut]} len={[t['tlen'] for t in ut]}")
