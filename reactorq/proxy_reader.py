"""Offline Reactor SIMULATOR (local MLX LLM) for experiments only. Never part of the submission.

It reads evidence packs (reactorq.build_packs format), builds the exact message the kit's client sends to Reactor
(client.build_message: question + notes + answer-format suffix, passages [E1].., the FINAL ANSWER [ref:..] protocol),
answers with a local model and parses the reply with the kit's own parser (final_answers, citations, INSUFFICIENT).
Every output line carries "proxy": true; reactorq.finalize refuses such lines, and outputs live under runs/proxy/.

    python -m reactorq.proxy_reader run   --packs P.jsonl --out runs/proxy/X.jsonl [--model M] [--limit N] [--qids F]
    python -m reactorq.proxy_reader calib --split dev --packs runs/proxy/packs/cal_packs.jsonl \
        --proxy runs/proxy/cal_proxy.jsonl --reactor runs/reactor/e1_results.jsonl runs/reactor/e1b_results.jsonl \
        [--resolve runs/proxy/resolve.txt]
    python -m reactorq.proxy_reader ab    --split dev --a runs/proxy/X_A.jsonl --b runs/proxy/X_B.jsonl [--split2 dev200 ...]
Needs: pip install mlx-lm (Apple Silicon). No torch, no embeddings, no Reactor key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import core.paths  # noqa: F401  (kit on sys.path)
from client import _INSUFFICIENT, build_message, citations, final_answers, parse_question_date  # upstream kit
from score import score_question  # upstream kit

from core.data import gold, read_jsonl
from core.types import SHORT

DEFAULT_MODEL = "mlx-community/Qwen2.5-14B-Instruct-4bit"
SYSTEM = ("You are Reactor, an assistant with long-term memory of the user's past conversations. Answer the user's "
          "question using only the evidence passages provided in the message. Follow the answer-format instructions "
          "in the message exactly, including the FINAL ANSWER line.")


def ref_for(qid: str) -> str:
    return hashlib.sha1(qid.encode()).hexdigest()[:8]


def message_for(p: dict) -> tuple[str, str, list[dict]]:
    ref = ref_for(p["question_id"] + p.get("pack_hash", ""))
    passages = [{"id": x.get("id"), "text": x["text"], **({"date": x["date"]} if x.get("date") else {})}
                for x in p["passages"]]
    return build_message(p["question_text"], passages, ref, parse_question_date(p["question_date"])), ref, passages


def run(args) -> None:
    from mlx_lm import generate, load
    try:
        from mlx_lm.sample_utils import make_sampler
        gen_kw = {"sampler": make_sampler(temp=0.0)}
    except Exception:  # older mlx-lm
        gen_kw = {"temp": 0.0}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["question_id"] + json.loads(l).get("pack_hash", "") for l in open(out)} if out.exists() else set()
    want = set(Path(args.qids).read_text().split()) if args.qids else None
    packs = [p for p in read_jsonl(Path(args.packs)) if (want is None or p["question_id"] in want)
             and p["question_id"] + p.get("pack_hash", "") not in done]
    if args.limit:
        packs = packs[: args.limit]
    model, tok = load(args.model)
    print(f"{len(packs)} packs to answer with {args.model}", flush=True)
    t_all = time.time()
    with open(out, "a", encoding="utf-8") as f:
        for i, p in enumerate(packs, 1):
            text, ref, passages = message_for(p)
            prompt = tok.apply_chat_template([{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
                                             add_generation_prompt=True, tokenize=False)
            t0 = time.time()
            reply = generate(model, tok, prompt=prompt, max_tokens=args.max_tokens, verbose=False, **gen_kw)
            dt = round(time.time() - t0, 1)
            finals = final_answers(reply)
            rec = {"proxy": True, "model": args.model, "question_id": p["question_id"], "pack_hash": p.get("pack_hash"),
                   "route": p.get("route"), "ref": ref, "reply": reply, "latency_s": dt}
            if ref in finals:
                ans = finals[ref]
                cited, unknown = citations(ans, passages)
                rec.update(status="answered", answer=ans, citations=cited, unknown_citations=unknown,
                           uncited=bool(passages) and not cited, abstained=bool(_INSUFFICIENT.match(ans)))
            else:
                rec.update(status="timeout")
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            el = time.time() - t_all
            print(f"[{i}/{len(packs)}] {p['question_id']} {rec['status']} {dt}s {str(rec.get('answer', ''))[:60]!r} "
                  f"(eta {el / i * (len(packs) - i) / 60:.0f} min)", flush=True)


# ---- scoring -------------------------------------------------------------------------------------------------------

def _pred(r: dict | None) -> dict | None:
    """client/proxy result line -> prediction, like the kit's predictions.py with --abstain-on agent,no-answer."""
    if r is None:
        return None
    if r.get("status") != "answered" or r.get("abstained"):
        return {"abstain": True, "answer": "", "citations": []}
    import re
    ans = re.sub(r"\s*\[\s*E\d+(?:\s*[,;]\s*E\d+)*\s*\]", "", r.get("answer") or "").strip()
    cites = list(dict.fromkeys(c["id"] for c in r.get("citations") or [] if c.get("id")))
    return {"abstain": False, "answer": ans, "citations": cites}


def _load(paths: list[str]) -> dict[str, dict]:
    best: dict[str, dict] = {}
    for f in paths:
        for r in read_jsonl(Path(f)):
            q = r.get("question_id")
            if q and (r.get("status") == "answered" or best.get(q, {}).get("status") != "answered"):
                best[q] = r
    return best


def _label(sq: dict, resolve: dict, key: str) -> str:
    if key in resolve:
        return resolve[key]
    return sq["answer"]  # correct | wrong | unjudged


def calib(args) -> int:
    g = gold(args.split)
    proxy, real = _load(args.proxy), _load(args.reactor)
    resolve = {}
    if args.resolve and Path(args.resolve).exists():
        for line in Path(args.resolve).read_text().split("\n"):
            if "=" in line:
                k, v = line.strip().split("=", 1)
                resolve[k.strip()] = v.strip()
    qids = [q for q in real if q in proxy and q in g and real[q].get("status") == "answered"]
    rows, n_fmt = [], 0
    print(f"{'qid':16s} {'type':9s} {'R':4s} {'P':4s}  reactor | proxy | gold")
    for q in qids:
        sr, sp = score_question(_pred(real[q]), g[q]), score_question(_pred(proxy[q]), g[q])
        lr, lp = _label(sr, resolve, f"R:{q}"), _label(sp, resolve, f"P:{q}")
        n_fmt += proxy[q].get("status") == "answered"
        rows.append((q, SHORT[g[q]["question_type"]], g[q]["abstain"], lr, lp))
        print(f"{q:16s} {SHORT[g[q]['question_type']]:9s} {lr[:4]:4s} {lp[:4]:4s}  "
              f"{str(_pred(real[q])['answer'] or 'ABSTAIN')[:28]!r} | {str(_pred(proxy[q])['answer'] or 'ABSTAIN')[:28]!r}"
              f" | {g[q]['answer'][:40]!r}")
    unj = [f"{w}:{q}" for q, _, _, lr, lp in rows for w, l in (("R", lr), ("P", lp)) if l == "unjudged"]
    n = len(rows)
    agree = sum(1 for r in rows if r[3] == r[4] and r[3] != "unjudged")
    r_err = [r for r in rows if r[3] == "wrong"]
    caught = sum(1 for r in r_err if r[4] == "wrong")
    unans = [r for r in rows if r[2]]
    p_abs_ok = sum(1 for r in unans if r[4] == "correct")
    p_false_abs = sum(1 for q, *_ in rows if not g[q]["abstain"] and _pred(proxy[q])["abstain"])
    r_false_abs = sum(1 for q, *_ in rows if not g[q]["abstain"] and _pred(real[q])["abstain"])
    lat = sorted(proxy[q].get("latency_s") or 0 for q in qids)
    med = lat[len(lat) // 2] if lat else 0
    checks = [
        ("format: FINAL ANSWER line parsed", n_fmt >= n - 1, f"{n_fmt}/{n}"),
        ("no unresolved 'unjudged' labels", not unj, f"{len(unj)} to resolve: {' '.join(unj)}"),
        ("agreement correct/wrong with Reactor >= 83%", agree >= 0.83 * n, f"{agree}/{n}"),
        ("catches Reactor's own errors (>= half)", (caught >= (len(r_err) + 1) // 2) if r_err else False,
         f"{caught}/{len(r_err)}"),
        ("abstains on unanswerable", p_abs_ok >= len(unans) - 1, f"{p_abs_ok}/{len(unans)}"),
        ("false abstentions <= Reactor's + 2", p_false_abs <= r_false_abs + 2, f"proxy {p_false_abs} vs Reactor {r_false_abs}"),
        ("speed: median <= 15 s/question", med <= 15, f"median {med}s"),
    ]
    print()
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name:46s} {detail}")
    go = all(ok for _, ok, _ in checks)
    print(f"\n==> {'GO' if go else 'STOP'}  (n={n}; with this n the test can reject a bad simulator, not prove a good one)")
    return 0 if go else 1


def ab(args) -> None:
    """Paired comparison of two variants answered by the SAME simulator on the same questions."""
    import statistics
    from score import evidence_f1
    golds = {}
    for s in args.split:
        golds.update(gold(s))
    A, B = _load(args.a), _load(args.b)
    qids = [q for q in A if q in B and q in golds]
    by_route: dict[str, list] = {}
    wins = losses = ties = unclear = 0
    f1a, f1b = [], []
    for q in qids:
        sa, sb = score_question(_pred(A[q]), golds[q]), score_question(_pred(B[q]), golds[q])
        la, lb = sa["answer"], sb["answer"]
        if "unjudged" in (la, lb):
            unclear += 1
            res = "?"
        elif la == lb:
            ties += 1
            res = "="
        elif la == "correct":
            wins += 1
            res = "A"
        else:
            losses += 1
            res = "B"
        by_route.setdefault(A[q].get("route") or "?", []).append(res)
        if sa["evidence_f1"] is not None:
            f1a.append(sa["evidence_f1"])
            f1b.append(sb["evidence_f1"])
    print(f"{len(qids)} paired questions: A better {wins}, B better {losses}, same {ties}, unjudged {unclear}")
    for r, v in sorted(by_route.items()):
        print(f"  {r:9s} A {v.count('A'):3d}  B {v.count('B'):3d}  = {v.count('='):3d}  ? {v.count('?'):3d}")
    if f1a:
        print(f"evidence F1: A {statistics.mean(f1a):.3f}  B {statistics.mean(f1b):.3f}")
    net = wins - losses
    decisive = wins + losses
    verdict = ("prefer A" if net >= 3 and wins >= 0.6 * max(1, decisive) else
               "prefer B" if -net >= 3 and losses >= 0.6 * max(1, decisive) else "no reliable difference")
    print(f"==> {verdict}  (rule: |net| >= 3 and >= 60% of decisive pairs; 'unjudged' rows need a look)")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--packs", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--model", default=DEFAULT_MODEL)
    r.add_argument("--limit", type=int)
    r.add_argument("--qids")
    r.add_argument("--max-tokens", type=int, default=600)
    c = sub.add_parser("calib")
    c.add_argument("--split", default="dev")
    c.add_argument("--proxy", nargs="+", required=True)
    c.add_argument("--reactor", nargs="+", required=True)
    c.add_argument("--resolve")
    c.add_argument("--packs")
    b = sub.add_parser("ab")
    b.add_argument("--split", nargs="+", default=["dev", "dev200"])
    b.add_argument("--a", nargs="+", required=True)
    b.add_argument("--b", nargs="+", required=True)
    a = ap.parse_args()
    if not str(getattr(a, "out", "runs/proxy/")).startswith(("runs/proxy", str(Path("runs/proxy").resolve()))):
        sys.exit("proxy outputs must go under runs/proxy/ (kept away from the submission)")
    if a.cmd == "run":
        run(a)
        return 0
    if a.cmd == "calib":
        return calib(a)
    ab(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
