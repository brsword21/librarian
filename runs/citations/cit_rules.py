"""Rule policies for citation attribution, evaluated on real Reactor answers (dev calibration) and test answers.

Run from librarian/:  .venv/bin/python <this file> calib|test|sim
Read-only on project files.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import core.paths  # noqa: F401
from score import normalize, evidence_f1  # kit
from predictions import strip_labels  # kit/reactor

from core.data import gold as load_gold, read_jsonl
from reactorq.finalize import attribute, _num

INSUFF = "INSUFFICIENT_EVIDENCE"
STOP = set("the a an of in on at to for and or my i me with from by is was it this that day days week weeks month months "
           "year years time times one two three four five six seven eight nine ten".split())


# ----------------------------------------------------------------------------------------------- helpers
def pred_from_result(r: dict) -> dict:
    ans = r.get("answer") or ""
    abst = r.get("status") != "answered" or INSUFF in ans or bool(r.get("abstained"))
    cites = list(dict.fromkeys(c["id"] for c in (r.get("citations") or []) if c.get("id")))
    return {"question_id": r["question_id"], "abstain": abst, "answer": "" if abst else strip_labels(ans),
            "citations": [] if abst else cites}


def norm_ans(answer: str) -> str:
    return normalize(strip_labels(answer or ""))


def contains(text: str, ans: str) -> bool:
    return bool(ans) and f" {ans} " in f" {normalize(text)} "


def specific(ans: str) -> bool:
    """Answer string distinctive enough that 'session contains it' means 'session supports it'."""
    toks = ans.split()
    if not toks:
        return False
    content = [t for t in toks if not t.isdigit() and t not in STOP and len(t) >= 3]
    if content:
        return True
    nums = [t for t in toks if t.replace(".", "").isdigit()]
    return any(len(t.replace(".", "")) >= 4 for t in nums)   # e.g. 37500, 2023; never a bare small count


DAYQ = re.compile(r"\bhow many (days|weeks|months|years)\b|\bhow long\b|\bhow old\b", re.I)


def computed_match(pred: dict, pack: dict, slack: bool = True) -> bool:
    c = pack.get("computed")
    if c is None:
        return False
    a, b = _num(pred["answer"]), _num(str(c))
    if a is None or b is None:
        return False
    if a == b:
        return True
    if slack and DAYQ.search(pack.get("question", "")):
        try:
            return abs(float(a) - float(b)) == 1
        except ValueError:
            return False
    return False


def passages(pack):
    return [p for p in pack["passages"] if p.get("id")]


# ----------------------------------------------------------------------------------------------- policies
def pol_a(pred, pack):
    return list(pred["citations"])


def pol_b(pred, pack):
    return attribute(pred, pack, True, True)[0]["citations"]


def pol_c(pred, pack, base=None):
    cites = list(base if base is not None else pol_b(pred, pack))
    if cites and computed_match(pred, pack):
        for s in pack.get("cite_plan") or []:
            if s and s not in cites:
                cites.append(s)
    return cites


def pol_c_strict(pred, pack):
    """computed-chain without the +/-1 slack."""
    cites = list(pol_b(pred, pack))
    if cites and computed_match(pred, pack, slack=False):
        for s in pack.get("cite_plan") or []:
            if s and s not in cites:
                cites.append(s)
    return cites


def pol_d(pred, pack):
    cites = list(pred["citations"])
    for s in pack.get("cite_plan") or []:
        if s and s not in cites:
            cites.append(s)
    return cites


def pol_e(pred, pack, guard=True, base=None):
    cites = list(base if base is not None else pol_b(pred, pack))
    ans = norm_ans(pred["answer"])
    if not cites or not ans or (guard and not specific(ans)):
        return cites
    for p in passages(pack):
        if p["id"] not in cites and contains(p["text"], ans):
            cites.append(p["id"])
    return cites


def pol_e_raw(pred, pack):
    return pol_e(pred, pack, guard=False)


def drop_unsupported(pred, pack, cites, guard=True):
    ans = norm_ans(pred["answer"])
    if len(cites) < 2 or not ans or (guard and not specific(ans)):
        return list(cites)
    text = {p["id"]: p["text"] for p in passages(pack)}
    has = [c for c in cites if contains(text.get(c, ""), ans)]
    return has if has else list(cites)


def pol_f(pred, pack):
    """drop own cites without the answer (when another own cite has it), then fill-missing + ku-chain."""
    own = drop_unsupported(pred, pack, pred["citations"])
    return attribute({**pred, "citations": own}, pack, True, True)[0]["citations"]


def pol_f_raw(pred, pack):
    own = drop_unsupported(pred, pack, pred["citations"], guard=False)
    return attribute({**pred, "citations": own}, pack, True, True)[0]["citations"]


def pol_rec(pred, pack):
    """recommended combination: b + computed-chain (temporal/multi computed) + guarded containment (ssu/ssa/ku only)."""
    cites = pol_c(pred, pack)
    if pack.get("route") in ("ssu", "ssa", "ku"):
        cites = pol_e(pred, pack, base=cites)
    return cites


POLICIES = {"a_own": pol_a, "b_finalize": pol_b, "c_computed": pol_c, "c_strict": pol_c_strict,
            "d_plan_union": pol_d, "e_contain_g": pol_e, "e_contain_raw": pol_e_raw,
            "f_drop_g": pol_f, "f_drop_raw": pol_f_raw, "rec": pol_rec}


# ----------------------------------------------------------------------------------------------- calibration
def calib():
    g = load_gold("dev")
    sets = {}
    for tag in ("e1", "e1b"):
        packs = {p["pack_hash"]: p for p in read_jsonl(Path(f"runs/reactor/{tag}_packs.jsonl"))}
        packs_q = {p["question_id"]: p for p in read_jsonl(Path(f"runs/reactor/{tag}_packs.jsonl"))}
        rows = []
        for r in read_jsonl(Path(f"runs/reactor/{tag}_results.jsonl")):
            pack = packs.get(r.get("pack_hash")) or packs_q.get(r["question_id"])
            rows.append((pred_from_result(r), pack, g[r["question_id"]], r))
        sets[tag] = rows
    out = []
    for tag, rows in sets.items():
        ans_rows = [x for x in rows if not x[2]["abstain"]]
        answered = [x for x in ans_rows if not x[0]["abstain"]]
        out.append(f"\n### {tag}: {len(rows)} results, {len(ans_rows)} answerable gold, {len(answered)} answered by Reactor\n")
        hdr = "| policy | F1 all answerable (n=%d) | F1 answered (n=%d) | changed qs |" % (len(ans_rows), len(answered))
        out.append(hdr)
        out.append("|---|---|---|---|")
        for name, fn in POLICIES.items():
            f_all, f_ans, ch = [], [], 0
            for pred, pack, gg, r in ans_rows:
                if pred["abstain"] or pack is None:
                    f_all.append(0.0)
                    continue
                c = fn(pred, pack)
                if set(c) != set(pred["citations"]):
                    ch += 1
                f = evidence_f1(c, gg["evidence"])
                f_all.append(f)
                f_ans.append(f)
            out.append(f"| {name} | {sum(f_all)/max(1,len(f_all)):.3f} | {sum(f_ans)/max(1,len(f_ans)):.3f} | {ch} |")
        out.append("\nPer question (answered, answerable):\n")
        out.append("| qid | route | gold type | answer | computed | gold ev | own | " + " | ".join(
            k for k in POLICIES if k != "a_own") + " |")
        out.append("|---" * (6 + len(POLICIES)) + "|")
        for pred, pack, gg, r in answered:
            if pack is None:
                continue
            gev = set(gg["evidence"])
            plan = pack.get("cite_plan") or []

            def fmt(c):
                f = evidence_f1(c, gg["evidence"])
                return f"{f:.2f} ({len(set(c)&gev)}/{len(c)})"
            cells = [fmt(fn(pred, pack)) for k, fn in POLICIES.items() if k != "a_own"]
            out.append(f"| {pred['question_id'][-6:]} | {pack['route']} | {gg['question_type'][:12]} | "
                       f"{pred['answer'][:28]!s} | {pack.get('computed')} | {len(gev)} (plan {len(set(plan)&gev)}/{len(plan)}) | "
                       f"{fmt(pred['citations'])} | " + " | ".join(cells) + " |")
    print("\n".join(out))


# ----------------------------------------------------------------------------------------------- test
def load_test():
    packs_h, packs_q = {}, {}
    for f in ("runs/final/v3_test_packs.jsonl", "runs/final/v2_test_packs.jsonl", "runs/final/v1_test_packs.jsonl",
              "runs/final/v1_rebuild_test_packs.jsonl", "runs/final/r1c_test_packs.jsonl",
              "runs/final/r1s_test_packs.jsonl", "runs/final/r1_test_packs.jsonl"):
        for p in read_jsonl(Path(f)):
            packs_h.setdefault(p["pack_hash"], p)
            packs_q.setdefault(p["question_id"], p)
    best = {}
    snap = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("runs/final/v1_results.jsonl")
    for r in read_jsonl(snap):
        qid = r["question_id"]
        if r.get("status") == "answered" or best.get(qid, {}).get("status") != "answered":
            best[qid] = r
    rows, nohash = [], 0
    for qid, r in best.items():
        pack = packs_h.get(r.get("pack_hash"))
        if pack is None:
            nohash += 1
            pack = packs_q.get(qid)
        rows.append((pred_from_result(r), pack, r))
    return rows, nohash


def snippet(text: str, ans: str, n=260):
    t = " ".join(text.split())
    if ans:
        nt = t.lower()
        # locate a raw-text hit of the first content token of the answer
        toks = [x for x in ans.split() if x not in STOP] or ans.split()
        i = nt.find(toks[0]) if toks else -1
        if i >= 0:
            s = max(0, i - n // 2)
            return ("…" if s else "") + t[s:s + n] + "…"
    return t[:n] + "…"


def test():
    rows, nohash = load_test()
    answered = [x for x in rows if not x[0]["abstain"]]
    out = [f"{len(rows)} questions with a result, {len(answered)} answered (non-abstained); {nohash} joined by qid "
           f"(pack hash not found)\n"]
    by_route = Counter(x[1]["route"] for x in answered if x[1])
    out.append("answered per route: " + ", ".join(f"{k} {v}" for k, v in sorted(by_route.items())) + "\n")
    out.append("| policy | questions changed | sessions added | sessions removed | changed per route |")
    out.append("|---|---|---|---|---|")
    examples = {}
    for name, fn in POLICIES.items():
        if name == "a_own":
            continue
        ch, add, rem, per = 0, 0, 0, Counter()
        ex = []
        for pred, pack, r in answered:
            if pack is None:
                continue
            c = fn(pred, pack)
            a = [s for s in c if s not in pred["citations"]]
            d = [s for s in pred["citations"] if s not in c]
            if a or d:
                ch += 1
                add += len(a)
                rem += len(d)
                per[pack["route"]] += 1
                ex.append((pred, pack, r, a, d))
        examples[name] = ex
        out.append(f"| {name} | {ch} | {add} | {rem} | " + ", ".join(f"{k} {v}" for k, v in sorted(per.items())) + " |")
    print("\n".join(out))
    return examples


def test_examples(examples, names, k=10):
    out = []
    for name in names:
        ex = examples.get(name, [])
        out.append(f"\n#### {name}: {len(ex)} changed questions" + (f" (first {k})" if len(ex) > k else "") + "\n")
        for pred, pack, r, a, d in ex[:k]:
            ans = norm_ans(pred["answer"])
            text = {p["id"]: (p["date"], p["text"]) for p in passages(pack)}
            idx = {p["id"]: i + 1 for i, p in enumerate(passages(pack))}
            out.append(f"- **{pred['question_id']}** [{pack['route']}] Q: {pack['question']}  \n"
                       f"  Reactor: `{(r.get('answer') or '')[:90]}` (cites {', '.join('E%d' % idx.get(c, 0) for c in pred['citations'])})"
                       f"; computed={pack.get('computed')}; cite_plan={', '.join('E%d' % idx.get(c, 0) for c in pack.get('cite_plan') or [])}")
            for s in a:
                dt, tx = text.get(s, ("?", ""))
                out.append(f"  - ADD E{idx.get(s, 0)} {s} ({dt}) contains answer: {contains(tx, ans)} — \"{snippet(tx, ans)}\"")
            for s in d:
                dt, tx = text.get(s, ("?", ""))
                out.append(f"  - DROP E{idx.get(s, 0)} {s} ({dt}) contains answer: {contains(tx, ans)} — \"{snippet(tx, ans)}\"")
    print("\n".join(out))


# ----------------------------------------------------------------------------------------------- dev simulation
def sim():
    """dev / dev200 packs built by the frozen system, gold answer standing in for Reactor's answer.

    Rule precision: of the sessions a rule adds (relative to the base), the share that are gold evidence; and F1 of
    the rule's output against gold, for two simulated Reactor citation behaviours:
      base=plan   Reactor cites exactly our cite_plan
      base=one    Reactor cites one session: the newest cite_plan session that contains the answer, else cite_plan[0]
                  (what we observed on ku / temporal)
    """
    out = []
    for split in ("dev", "dev200"):
        g = load_gold(split)
        packs = list(read_jsonl(Path(f"runs/citations/{split}_packs.jsonl")))
        out.append(f"\n### {split}: {len(packs)} packs\n")
        stats = defaultdict(lambda: defaultdict(list))
        add_prec = defaultdict(lambda: [0, 0])
        for pack in packs:
            gg = g[pack["question_id"]]
            if gg["abstain"]:
                continue
            route = pack["route"]
            plan = [s for s in pack.get("cite_plan") or [] if s]
            pred_ans = gg["answer"]
            ans = norm_ans(pred_ans)
            text = {p["id"]: p["text"] for p in passages(pack)}
            has = [s for s in plan if contains(text.get(s, ""), ans)]
            one = [has[-1]] if has else plan[:1]
            for bname, base in (("plan", plan), ("one", one)):
                pred = {"question_id": pack["question_id"], "abstain": False, "answer": pred_ans,
                        "citations": list(base)}
                for name, fn in POLICIES.items():
                    c = fn(pred, pack)
                    f = evidence_f1(c, gg["evidence"])
                    stats[(bname, name)][route].append(f)
                    stats[(bname, name)]["ALL"].append(f)
                    if bname == "one":
                        for s in c:
                            if s not in base:
                                add_prec[(name, route)][0] += s in gg["evidence"]
                                add_prec[(name, route)][1] += 1
        routes = ["ssu", "ssa", "multi", "ku", "temporal", "ALL"]
        out.append("| base | policy | " + " | ".join(routes) + " |")
        out.append("|---|---|" + "---|" * len(routes))
        for (bname, name), d in stats.items():
            if bname == "plan" and name not in ("a_own", "c_computed", "e_contain_g", "e_contain_raw", "f_drop_g", "f_drop_raw", "rec"):
                continue
            out.append(f"| {bname} | {name} | " + " | ".join(
                f"{sum(d[r])/len(d[r]):.3f} (n={len(d[r])})" if d.get(r) else "-" for r in routes) + " |")
        out.append("\nPrecision of added sessions (base=one): gold/added per route\n")
        out.append("| policy | " + " | ".join(routes[:-1]) + " |")
        out.append("|---|" + "---|" * (len(routes) - 1))
        for name in POLICIES:
            cells = []
            for r in routes[:-1]:
                h, n = add_prec.get((name, r), [0, 0])
                cells.append(f"{h}/{n}" + (f" ({h/n:.2f})" if n else ""))
            out.append(f"| {name} | " + " | ".join(cells) + " |")
    print("\n".join(out))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "calib":
        calib()
    elif cmd == "test":
        ex = test()
        test_examples(ex, [n for n in POLICIES if n not in ("a_own",)])
    elif cmd == "sim":
        sim()


# ----------------------------------------------------------------------------------------------- round 2 rules
def _stem(t: str) -> str:
    if len(t) > 4 and t.endswith("es"):
        return t[:-2]
    if len(t) > 3 and t.endswith("s"):
        return t[:-1]
    return t


def _stoks(s: str) -> list[str]:
    return [_stem(t) for t in normalize(s).split()]


def supports(text: str, answer: str, question: str = "") -> bool:
    """exact phrase, else plural/hyphen-insensitive phrase, else for a bare number N: 'N <question noun>'."""
    ans = norm_ans(answer)
    if not ans:
        return False
    if contains(text, ans):
        return True
    a, t = _stoks(strip_labels(answer)), _stoks(text)
    if not a:
        return False
    ts = " " + " ".join(t) + " "
    if (len(a) > 1 or not a[0].isdigit()) and f" {' '.join(a)} " in ts:
        return True
    if len(a) == 1 and a[0].replace(".", "").isdigit() and question:
        nouns = {x for x in _stoks(question) if len(x) >= 4 and x not in STOP and not x.isdigit()}
        for i, x in enumerate(t):
            if x == a[0] and any(y in nouns for y in t[i + 1:i + 4]):
                return True
    return False


def specific2(ans_text: str) -> bool:
    """>= 2 content tokens, or a >= 4-digit number (single words like 'Masa' match decoys: 'masa madre')."""
    toks = norm_ans(ans_text).split()
    content = [t for t in toks if not t.isdigit() and t not in STOP and len(t) >= 3]
    return len(content) >= 2 or any(len(t.replace(".", "")) >= 4 and t.replace(".", "").isdigit() for t in toks)


def finalize2(pred, pack):
    """proposed finalize.attribute: fuzzy fill-missing + ku-chain only when Reactor cited exactly one session."""
    cites = list(pred["citations"])
    if not cites:
        sup = [p["id"] for p in passages(pack) if supports(p["text"], pred["answer"], pack.get("question", ""))]
        if not sup and computed_match(pred, pack):
            sup = [s for s in pack.get("cite_plan") or [] if s]
        cites = list(dict.fromkeys(sup))
    if pack.get("route") == "ku" and len(cites) == 1:
        plan = [s for s in (pack.get("cite_plan") or []) if s]
        if len(plan) == 2 and cites[0] in plan:
            cites.append([s for s in plan if s != cites[0]][0])
    return cites


ROW_BAD = re.compile(r"(?i)exclud|\bnot\b|ignor|decoy|reject|✗|drop|outside|skip|plan(?:ned|s)?\b|other person|friend|"
                     r"no user|never|n't|irrelevant|unrelated")
ROW_E = re.compile(r"\[?E(\d+)\]?")


def reply_rows(reply: str) -> list[int]:
    """[E#] of the instance rows Reactor listed in its own working (multi format 'date | [E#] | item | n')."""
    body = (reply or "").split("# FINAL ANSWER")[0]
    out = []
    for line in body.splitlines():
        s = line.strip()
        if re.match(r"(?i)^(excluded|decoys?|notes? on what|choices|two things|the one|\(excluded)", s):
            break
        if not (("|" in s or "→" in s) and ROW_E.search(s)) or ROW_BAD.search(s):
            continue
        es = ROW_E.findall(s)
        if len(set(es)) == 1:
            out.append(int(es[0]))
    return out


def pol_g(pred, pack, reply=""):
    cites = finalize2(pred, pack)
    if pack.get("route") != "multi" or not cites:
        return cites
    ids = [p["id"] for p in passages(pack)]
    for k in reply_rows(reply):
        if 1 <= k <= len(ids) and ids[k - 1] not in cites:
            cites.append(ids[k - 1])
    return cites


def rec2(pred, pack, reply=""):
    """finalize2 + computed-chain + guarded containment (ssu/ssa/ku/temporal, >=2-token answers) + multi reply rows."""
    cites = pol_g(pred, pack, reply)
    cites = pol_c(pred, pack, base=cites)
    if cites and pack.get("route") in ("ssu", "ssa", "ku", "temporal") and specific2(pred["answer"]):
        ans = norm_ans(pred["answer"])
        for p in passages(pack):
            if p["id"] not in cites and contains(p["text"], ans):
                cites.append(p["id"])
    return cites


def e2(pred, pack):
    cites = finalize2(pred, pack)
    if cites and specific2(pred["answer"]) and pack.get("route") != "multi":
        ans = norm_ans(pred["answer"])
        for p in passages(pack):
            if p["id"] not in cites and contains(p["text"], ans):
                cites.append(p["id"])
    return cites


R2 = {"b_finalize": lambda p, k, r: pol_b(p, k), "b2_finalize2": lambda p, k, r: finalize2(p, k),
      "c2_computed": lambda p, k, r: pol_c(p, k, base=finalize2(p, k)),
      "e2_contain2": lambda p, k, r: e2(p, k), "g_reply_rows": pol_g, "rec2": rec2}


def run2(which):
    if which == "calib":
        g = load_gold("dev")
        for tag in ("e1", "e1b"):
            packs = {p["pack_hash"]: p for p in read_jsonl(Path(f"runs/reactor/{tag}_packs.jsonl"))}
            rows = [(pred_from_result(r), packs.get(r.get("pack_hash")), g[r["question_id"]], r)
                    for r in read_jsonl(Path(f"runs/reactor/{tag}_results.jsonl"))]
            rows = [x for x in rows if not x[2]["abstain"]]
            print(f"\n{tag}: answerable {len(rows)}, answered {sum(not x[0]['abstain'] for x in rows)}")
            print("| policy | F1 all answerable | F1 answered | changed | per-question F1 (answered) |\n|---|---|---|---|---|")
            for name, fn in R2.items():
                fa, fn_ans, ch, per = [], [], 0, []
                for pred, pack, gg, r in rows:
                    if pred["abstain"] or pack is None:
                        fa.append(0.0)
                        continue
                    c = fn(pred, pack, r.get("reply", ""))
                    ch += set(c) != set(pred["citations"])
                    f = evidence_f1(c, gg["evidence"])
                    fa.append(f)
                    fn_ans.append(f)
                    per.append(f"{f:.2f}")
                print(f"| {name} | {sum(fa)/len(fa):.3f} | {sum(fn_ans)/max(1,len(fn_ans)):.3f} | {ch} | {' '.join(per)} |")
    elif which == "test":
        rows, _ = load_test()
        answered = [x for x in rows if not x[0]["abstain"] and x[1]]
        print(f"\n{len(answered)} answered test questions\n")
        print("| policy | changed | added | removed | per route |\n|---|---|---|---|---|")
        ex = {}
        for name, fn in R2.items():
            ch, ad, rm, per, lst = 0, 0, 0, Counter(), []
            for pred, pack, r in answered:
                c = fn(pred, pack, r.get("reply", ""))
                a = [s for s in c if s not in pred["citations"]]
                d = [s for s in pred["citations"] if s not in c]
                if a or d:
                    ch += 1; ad += len(a); rm += len(d); per[pack["route"]] += 1
                    lst.append((pred, pack, r, a, d))
            ex[name] = lst
            print(f"| {name} | {ch} | {ad} | {rm} | {', '.join(f'{k} {v}' for k, v in sorted(per.items()))} |")
        test_examples(ex, ["b2_finalize2", "g_reply_rows", "rec2"])
    elif which == "sim":
        for split in ("dev", "dev200"):
            g = load_gold(split)
            res = defaultdict(lambda: defaultdict(list))
            addp = defaultdict(lambda: [0, 0])
            for pack in read_jsonl(Path(f"runs/citations/{split}_packs.jsonl")):
                gg = g[pack["question_id"]]
                if gg["abstain"]:
                    continue
                plan = [s for s in pack.get("cite_plan") or [] if s]
                ans = norm_ans(gg["answer"])
                text = {p["id"]: p["text"] for p in passages(pack)}
                has = [s for s in plan if contains(text.get(s, ""), ans)]
                for bname, base in (("none", []), ("one", [has[-1]] if has else plan[:1]), ("plan", plan)):
                    pred = {"question_id": pack["question_id"], "abstain": False, "answer": gg["answer"],
                            "citations": list(base)}
                    for name in ("b_finalize", "b2_finalize2", "c2_computed", "e2_contain2", "rec2"):
                        c = R2[name](pred, pack, "")
                        f = evidence_f1(c, gg["evidence"])
                        res[(bname, name)][pack["route"]].append(f)
                        res[(bname, name)]["ALL"].append(f)
                        for s in c:
                            if s not in base:
                                addp[(bname, name)][0] += s in gg["evidence"]
                                addp[(bname, name)][1] += 1
            routes = ["ssu", "ssa", "multi", "ku", "temporal", "ALL"]
            print(f"\n{split}\n| base | policy | " + " | ".join(routes) + " | added gold/added |\n|---|---|" + "---|" * (len(routes) + 1))
            for (b, n), d in res.items():
                h, m = addp[(b, n)]
                print(f"| {b} | {n} | " + " | ".join(f"{sum(d[r])/len(d[r]):.3f}" if d.get(r) else "-" for r in routes)
                      + f" | {h}/{m}" + (f" ({h/m:.2f})" if m else "") + " |")


if __name__ == "__main__" and sys.argv[1].endswith("2"):
    run2(sys.argv[1][:-1])
