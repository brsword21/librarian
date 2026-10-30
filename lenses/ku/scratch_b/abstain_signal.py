"""Lexical-coverage abstention signals (BM25 only) -> AUC on dev / dev200 (all types and KU only)."""
import re, sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import Stemmer
from core.data import gold, questions
from core.index import HistoryIndex

ST = Stemmer.Stemmer("english")
STOP = set("""a an the of in on at to for from by with and or but is are was were be been being do does did have has had
i me my mine we our you your he she it they them his her its their this that these those what which who whom whose where when
why how many much often long time times there here so far now currently current right still ever yet just very also
can could would should will shall may might must am about into than then as if not no any some all each every more most
own get got go going went use using used up out over again since last first previous previously recently recent
total number amount kind type name called""".split())
TOK = re.compile(r"[A-Za-z][A-Za-z0-9'\-]+|\d[\d,.:/-]*")

def terms(text):
    out = []
    for w in TOK.findall(text):
        wl = w.lower().strip("'").replace("'s", "")
        if wl in STOP or len(wl) < 3:
            continue
        out.append(ST.stemWord(wl))
    return out

def auc(pos, neg):
    if not pos or not neg:
        return float("nan")
    c = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return c / (len(pos) * len(neg))

def run(split, only_ku):
    g = gold(split)
    feats = {"miss_hist": ([], []), "miss_top1": ([], []), "miss_best3": ([], []), "idfmiss_best3": ([], [])}
    for q in questions(split):
        gg = g[q.question_id]
        if only_ku and gg["question_type"] != "knowledge-update":
            continue
        hx = HistoryIndex.load(split, q.history_id)
        qt = list(dict.fromkeys(terms(q.question)))
        if not qt:
            continue
        user_units = [u for u in hx.units if u.role == "user"]
        df = {t: 0 for t in qt}
        uterms = {}
        for u in user_units:
            s = set(terms(u.index_text))
            uterms[u.uid] = s
            for t in qt:
                if t in s:
                    df[t] += 1
        N = len(user_units)
        idf = {t: math.log((N + 1) / (df[t] + 0.5)) for t in qt}
        top = [uid for uid, _ in hx.bm25(q.question, k=3, roles="user")]
        f = {}
        f["miss_hist"] = sum(df[t] == 0 for t in qt)
        f["miss_top1"] = sum(t not in uterms.get(top[0], set()) for t in qt) / len(qt) if top else 1
        f["miss_best3"] = min((sum(t not in uterms[u] for t in qt) for u in top), default=len(qt)) / len(qt)
        f["idfmiss_best3"] = min((sum(idf[t] for t in qt if t not in uterms[u]) for u in top), default=99) / sum(idf.values())
        for k, v in f.items():
            feats[k][0 if gg["abstain"] else 1].append(v)
    print(split, "KU only" if only_ku else "all types", "abstain n =", len(feats["miss_hist"][0]), "answerable n =", len(feats["miss_hist"][1]))
    for k, (pos, neg) in feats.items():
        print(f"   {k:14s} AUC={auc(pos, neg):.3f}  mean abst={sum(pos)/len(pos):.2f} ans={sum(neg)/len(neg):.2f}")

for split in sys.argv[1:] or ["dev"]:
    run(split, True)
    run(split, False)
