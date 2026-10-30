"""Exploratory stats for multi-session questions (dev). Plain json + re only.

    .venv/bin/python lenses/multi/scratch_b/analyze.py [dev|dev200]
"""
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT.parent / "data"
split = sys.argv[1] if len(sys.argv) > 1 else "dev"

def rj(p):
    return [json.loads(l) for l in open(p) if l.strip()]

qs = {q["question_id"]: q for q in rj(DATA / split / "questions.jsonl")}
gold = {g["question_id"]: g for g in rj(DATA / split / "gold.jsonl")}
gt = json.load(open(ROOT / "cache/gold_turns.json"))
F = "%Y/%m/%d (%a) %H:%M"

multi = [qid for qid, g in gold.items() if g["question_type"] == "multi-session"]
print(split, "multi questions:", len(multi), "abstain:", sum(gold[q]["abstain"] for q in multi))

STOP = set("""a an the i my me we our you your of in on at to for from by with and or is are was were be been do did does
have has had how many much what which when who whom where why that this these those it its as about since than
total times time different all any some there their they them he she his her am not no can could would should will
so if but just also have i've i'm in""".split())
tok = lambda s: [w for w in re.findall(r"[a-z0-9]+", s.lower())]

def stem(w):
    for suf in ("ies", "es", "s", "ing", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w

starts = Counter()
window_phr = Counter()
role_c = Counter()
gold_sess_n = Counter()
turns_per_gs = Counter()
same_day = 0
spread_days = []
pos_frac = []
rank_list = []
dup_fact = 0
gold_turn_idx = Counter()
WIN = re.compile(r"\b(since [a-z]+|in (january|february|march|april|may|june|july|august|september|october|november|december)|"
                 r"(last|past|this) (few )?(week|weeks|month|months|year|summer|spring|winter|fall|weekend)|"
                 r"recently|currently|these days|so far|in total|this year|the month of \w+|last \w+|past two weeks|now)\b")
for qid in multi:
    q, g = qs[qid], gold[qid]
    text = q["question"]
    starts[" ".join(text.split()[:3])] += 1
    for m in WIN.finditer(text.lower()):
        window_phr[m.group(0)] += 1
    if g["abstain"]:
        continue
    h = json.load(open(ROOT / f"cache/hist/{split}/{q['history_id']}.json"))
    sess = h["sessions"]
    idx = {s["session_id"]: i for i, s in enumerate(sess)}
    qd = datetime.strptime(q["question_date"], F)
    ev = g["evidence"]
    gold_sess_n[len(ev)] += 1
    ds = [datetime.strptime(sess[idx[s]]["date"], F) for s in ev if s in idx]
    if ds:
        spread_days.append((qd - min(ds)).days)
        same_day += all(d.date() == qd.date() for d in ds)
    for s in ev:
        if s in idx:
            pos_frac.append(idx[s] / max(1, len(sess) - 1))
    tids = set(gt.get(qid, []))
    tmap = {}
    for s in sess:
        for i, t in enumerate(s["turns"]):
            tmap[t["turn_id"]] = (s["session_id"], i, t)
    per_s = Counter()
    for tid in tids:
        if tid in tmap:
            sid, i, t = tmap[tid]
            role_c[t["role"]] += 1
            per_s[sid] += 1
            gold_turn_idx[min(i, 10)] += 1
    for s in ev:
        turns_per_gs[per_s.get(s, 0)] += 1
    # simple TF-IDF turn ranking (user turns only) -> rank of each gold turn
    docs = [(tid, v[2]["content"]) for tid, v in tmap.items() if v[2]["role"] == "user"]
    df = Counter()
    dtoks = {}
    for tid, c in docs:
        ts = [stem(w) for w in tok(c) if w not in STOP]
        dtoks[tid] = Counter(ts)
        df.update(set(ts))
    N = len(docs)
    qt = [stem(w) for w in tok(text) if w not in STOP]
    sc = {}
    for tid, tf in dtoks.items():
        sc[tid] = sum((1 + math.log(tf[w])) * math.log(N / df[w]) for w in qt if tf.get(w))
    order = sorted(sc, key=lambda t: -sc[t])
    rk = {t: i for i, t in enumerate(order)}
    for tid in tids:
        if tid in rk:
            rank_list.append(rk[tid])

print("question starts:", starts.most_common(12))
print("window phrases:", window_phr.most_common(25))
print("gold #sessions:", sorted(gold_sess_n.items()))
print("gold turns per gold session:", sorted(turns_per_gs.items()))
print("gold turn roles:", role_c)
print("gold turn idx in session:", sorted(gold_turn_idx.items()))
print("all gold sessions on question day:", same_day, "/", sum(gold_sess_n.values()))
print("days from oldest gold session to question: median", sorted(spread_days)[len(spread_days)//2],
      "max", max(spread_days), "dist", Counter(min(d // 7, 10) for d in spread_days))
pf = sorted(pos_frac)
print("gold session position fraction quartiles", [round(pf[int(len(pf) * x)], 2) for x in (0.1, .25, .5, .75, .9)])
rl = sorted(rank_list)
print("tfidf rank of gold USER turns: n", len(rl), "r@5", sum(r < 5 for r in rl) / len(rl), "r@10",
      sum(r < 10 for r in rl) / len(rl), "r@20", sum(r < 20 for r in rl) / len(rl), "r@50", sum(r < 50 for r in rl) / len(rl),
      "median", rl[len(rl) // 2])
