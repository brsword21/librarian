"""Model-free proxy of b_evcal.rank_event: score = 6*overlap (stand-in for the cross-encoder) + the lens features.
dev: HA (computed vs gold number, N or N+1) and top-pick session in gold.  test: print the picks (qualitative only).
usage: proxy_eval.py dev|dev200|test [--nofeat] [--show]"""
import json
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, ".")
from core.data import parse_date  # noqa: E402
from core.units import build_units  # noqa: E402
from lenses.temporal import b_evcal as L  # noqa: E402

split = sys.argv[1]
nofeat = "--nofeat" in sys.argv
show = "--show" in sys.argv
D = {"dev": "../data/dev", "dev200": "../data/dev200", "test": "../data/test"}[split]
qs = [json.loads(l) for l in open(f"{D}/questions.jsonl")]
gold = {}
try:
    gold = {json.loads(l)["question_id"]: json.loads(l) for l in open(f"{D}/gold.jsonl")}
except FileNotFoundError:
    pass
P = dict(L.VARIANTS["evcal"])
if nofeat:
    P.update(w_date=0, w_self=0, w_other=0, w_neg=0, w_year=0, time_prior=False)


def first_num(s):
    m = re.search(r"\d+", s or "")
    if m:
        return int(m.group(0))
    w = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    for k, v in w.items():
        if re.search(rf"\b{k}\b", s or "", re.I):
            return v
    return None


def rank(units, qd, event, spec, anchor):
    ev = L.content_tokens(event)
    qp = L.question_persons(event)
    rows = []
    for u in units:
        if u.date > qd + timedelta(days=1):
            continue
        sent, ov = L.best_sentence(u.text, ev)
        if ov <= 0:
            continue
        d, how = L.resolve_date(sent, u.text, u.date, ev)
        subj = L.subject_class(sent, u.role, qp)
        f = 6.0 * ov + P["w_lex"] * ov
        f += P["w_date"] * (1.0 if how == "explicit" else 0.3 if how == "relative" else 0.0)
        f += P["w_self"] * (subj == "self") - P["w_other"] * (subj == "other")
        if L.contrast_hit(sent, ev):
            f -= P["w_neg"]
        if L._VARIANT.search(sent):
            f -= 0.3 * P["w_neg"]
        if spec.get("this_year") and how == "explicit" and d.year != qd.year:
            f -= P["w_year"]
        elif how == "explicit" and (u.date.date() - d).days > 200:
            f -= 0.5 * P["w_year"]
        if anchor is not None and P.get("time_prior"):
            import math
            f += 2.0 * math.exp(-abs((d - anchor[0]).days) / max(2, anchor[1]))
        rows.append((f, u, d, how, subj, sent.strip()))
    rows.sort(key=lambda r: -r[0])
    return rows


stats = {"n": 0, "parsed": 0, "computed": 0, "ha": 0, "sess_hit": 0, "ev": 0}
hist_cache = {}
for q in qs:
    g = gold.get(q["question_id"])
    if g is not None and (g["question_type"] != "temporal-reasoning" or g["abstain"]):
        continue
    if g is None and not re.search(r"how many days (apart|after)", q["question"], re.I):
        continue
    stats["n"] += 1
    spec = L.parse_question(q["question"])
    if not spec["events"]:
        continue
    stats["parsed"] += 1
    if q["history_id"] not in hist_cache:
        hist_cache.clear()
        h = json.load(open(f"cache/hist/{split}/{q['history_id']}.json"))
        hist_cache[q["history_id"]] = build_units(h)[0]
    units = hist_cache[q["history_id"]]
    qd = parse_date(q["question_date"])
    picks = []
    for ev in spec["events"]:
        r = rank(units, qd, ev, spec, None)
        if r:
            picks.append(r[0])
            stats["ev"] += 1
            if g and r[0][1].session_id in g["evidence"]:
                stats["sess_hit"] += 1
    ans = L.compute_answer(spec, [p[2] for p in picks], qd) if len(picks) == len(spec["events"]) else None
    if ans is not None:
        stats["computed"] += 1
    gn = first_num(g["answer"]) if g else None
    ok = ans is not None and gn is not None and (ans == gn or ans == gn + 1)
    stats["ha"] += ok
    if show or (g and ans is not None and not ok):
        print(("OK  " if ok else "MISS") if g else "TEST", "|", q["question"][:110], "| gold:", (g or {}).get("answer", "")[:30], "| ours:", ans, spec["unit"])
        for (f, u, d, how, subj, sent), ev in zip(picks, spec["events"]):
            print(f"      [{ev[:40]}] {d} {how} {subj} {u.role[:4]} sess={u.date_str[:10]} f={f:.2f} | {sent[:150]}")
print(split, stats)
