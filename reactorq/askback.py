"""Ask-back: Reactor searches the user's memory itself when our evidence pack is not enough.

Round 1  Reactor gets our pack as usual, plus a private link to the user's archive (reactorq/memory.py, served by
         demo/server.py through a public tunnel) and is told to search it before concluding.
Round 2  If Reactor searched, it is asked again in the SAME Reactor history (it remembers round 1) with our pack plus
         every passage it pulled up, labelled [E#], so its final answer cites real session ids.
Nothing is chosen by hand: the passages are exactly what Reactor's own queries returned (logged by the server).

    # 0. demo server + tunnel (tools/tunnel.sh prints the public URL)
    python -m demo.server --web demo/web_min --port 8800 &   sh tools/tunnel.sh 8800
    # 1. smoke test: does Reactor open a link at all? (one call, ~1 min)
    python -m reactorq.askback --smoke --public-url https://xxxx.trycloudflare.com
    # 2. the abstained test questions (default) or --qids q1,q2; --dry-run simulates Reactor's searches (no Reactor)
    python -m reactorq.askback --public-url https://xxxx.trycloudflare.com [--dry-run]
Writes runs/askback/results.jsonl (reactorq.finalize-compatible lines) and demo/askback.json (for the demo).
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

import core.paths  # noqa: F401
from core.paths import ROOT
from reactorq import memory

SUFFIX = ("Write the final answer line as: only the answer itself (a name, number, date or short phrase), followed by "
          "the [E#] label(s) of the passage(s) that state it. No explanation, no alternatives.")
ASK = ("The passages below were picked automatically from this user's past chats and may miss the answer. You can "
       "search the user's whole chat archive yourself: open {base}/search?q=<a few words> (plain text: "
       "[session id | date] then the matching turns). Before you conclude anything, and always before you answer "
       "INSUFFICIENT_EVIDENCE, search it with 1-3 different short queries (other words, the specific name or event). "
       "Then answer from everything you read.")
ROUND2 = ("Your archive searches are done. Below is the original evidence plus every passage your searches returned. "
          "Answer from these passages only.")
STOP = set("what which who whom whose when where why how is was were are do did does the a an of to in on for my i me "
           "name called many much days after before since last first ever have has had that this with and or our at "
           "by it its be been from end up ended you your right now current currently".split())
OUT = ROOT / "runs" / "askback" / "results.jsonl"
DEMO = ROOT / "demo" / "askback.json"


def strip_labels(s: str) -> str:
    return re.sub(r"\s*\[\s*E\d+(?:\s*[,;]\s*E\d+)*\s*\]", "", s or "").strip()


def simulated_queries(question: str) -> list[str]:
    """Dry run only: two short keyword queries, standing in for Reactor's own (labelled 'simulated' everywhere)."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]+", question.lower()) if w not in STOP]
    words = [w[:-2] if w.endswith("'s") else w for w in words]
    qs = [" ".join(words)]
    if len(words) > 2:
        qs.append(" ".join(words[-2:]))
    return [q for q in dict.fromkeys(qs) if q]


def load_records(split: str) -> dict[str, dict]:
    d = json.loads((ROOT / "demo" / "replay.json").read_text(encoding="utf-8"))
    return {r["question_id"]: r for r in d.get(split, [])}


def merge_evidence(passages: list[dict], hits: list[dict], budget: int = 26000) -> list[dict]:
    out, seen, used = [], set(), 0
    for p in passages + hits:
        key = (p.get("id"), p["text"][:200])
        if key in seen:
            continue
        if used + len(p["text"]) > budget and out:
            continue
        seen.add(key)
        used += len(p["text"])
        out.append({k: p[k] for k in ("id", "date", "text") if p.get(k) is not None})
    return out


def ask(rh: str, text: str, date: str, qid: str, passages: list[dict], timeout: float) -> dict:
    from reactorq.queue import call
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(passages, f, ensure_ascii=False)
    args = ["--history", rh, "--question", text, "--question-date", date, "--question-id", qid, "--max-chars", "32000"]
    if passages:
        args += ["--evidence", f.name]
    return call(*args, timeout=timeout)


def new_history() -> str:
    from reactorq.queue import call
    for attempt in range(5):
        nh = call("--new-history", timeout=120)
        if nh.get("status") == "history":
            return nh["history_id"]
        time.sleep(10 * (attempt + 1))
    raise SystemExit(f"new-history failed: {nh}")


def run_one(r: dict, split: str, base_url: str, rh: str, timeout: float = 600, askback: bool = True,
            on_stage=None, on_token=None) -> dict:
    """One question against Reactor (live demo and CLI). r: a pack record (question, question_date, history_id,
    question_id, notes, passages). askback=False is a plain ask (round 1 without the archive link).
    Returns {"first", "final", "searches", "res"}; the searches are what Reactor's own queries returned."""
    stage = on_stage or (lambda s: None)
    passages = [{k: p[k] for k in ("id", "date", "text") if p.get(k) is not None} for p in r["passages"]]
    notes = (r.get("notes") or "").strip()
    tok = memory.new_token(split, r["history_id"], r["question_id"])
    if on_token:
        on_token(tok)
    stage("round1")
    ask_line = ASK.format(base=f"{base_url.rstrip('/')}/m/{tok}") if askback else ""
    text1 = "\n".join(x for x in (r["question"], notes, ask_line, SUFFIX) if x)
    res = ask(rh, text1, r["question_date"], r["question_id"], passages, timeout)
    first = {"answer": strip_labels(res.get("answer")), "abstained": bool(res.get("abstained")),
             "status": res.get("status")}
    final = {**first, "cited": [c["id"] for c in res.get("citations") or [] if c.get("id")]}
    searches = [{"q": s["q"], "hits": s["hits"]} for s in memory.requests_for(tok)]
    if askback and searches:
        stage("round2")
        ev = merge_evidence(passages, [h for s in searches for h in s["hits"]])
        text2 = "\n".join(x for x in (r["question"], notes, ROUND2, SUFFIX) if x)
        res2 = ask(rh, text2, r["question_date"], r["question_id"], ev, timeout)
        if res2.get("status") == "answered":
            res = res2
            final = {"answer": strip_labels(res2.get("answer")), "abstained": bool(res2.get("abstained")),
                     "cited": [c["id"] for c in res2.get("citations") or [] if c.get("id")]}
    stage("done")
    return {"first": first, "final": final, "searches": searches, "res": res, "token": tok}


def smoke(base_url: str, timeout: float) -> int:
    """One question, no evidence: can Reactor open our link? Prints what the server saw."""
    rec = next(iter(load_records("test").values()))
    tok = memory.new_token("test", rec["history_id"], "smoke")
    url = f"{base_url.rstrip('/')}/m/{tok}/search?q=dog+name"
    rh = new_history()
    t0 = time.time()
    res = ask(rh, f"Open this web page and tell me the first session id it lists (it starts with s_): {url}",
              rec["question_date"], "smoke", [], timeout)
    seen = memory.requests_for(tok)
    print(json.dumps({"status": res.get("status"), "answer": res.get("answer"), "server_saw": len(seen),
                      "queries": [r["q"] for r in seen], "wall_s": round(time.time() - t0, 1)}, indent=1))
    print("OK: Reactor reads our memory links." if seen else
          "NO REQUEST reached the server: Reactor did not open the link (check the tunnel URL in a browser).")
    return 0 if seen else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--public-url", help="tunnel base URL that reaches demo.server (tools/tunnel.sh)")
    ap.add_argument("--split", default="test")
    ap.add_argument("--qids", help="comma-separated; default: questions abstained in --predictions")
    ap.add_argument("--predictions", default=str(ROOT / "submission" / "predictions.jsonl"))
    ap.add_argument("--dry-run", action="store_true", help="no Reactor: simulate its searches through the public URL")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--timeout", type=float, default=600)
    a = ap.parse_args(argv)
    if not a.public_url:
        ap.error("--public-url is required (the searches must go through the server, so they are logged)")
    base_url = a.public_url.rstrip("/")
    if a.smoke:
        return smoke(base_url, a.timeout)

    recs = load_records(a.split)
    if a.qids:
        qids = a.qids.split(",")
    else:
        preds = [json.loads(l) for l in open(a.predictions, encoding="utf-8") if l.strip()]
        qids = [p["question_id"] for p in preds if p["abstain"]]
    demo = json.loads(DEMO.read_text(encoding="utf-8")) if DEMO.exists() else {}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    histories: dict[str, str] = {}
    for n, qid in enumerate(qids, 1):
        split = a.split
        r = recs.get(qid)
        if r is None:   # not in the replay (e.g. a dev question): build the v3 pack now
            from demo.server import make_question, pack_for
            split = make_question({"question_id": qid})[0]
            r = {**pack_for({"question_id": qid}), "answer": None, "abstained": None}
        t0 = time.time()
        if a.dry_run:
            tok = memory.new_token(split, r["history_id"], qid)
            first = {"answer": r.get("answer"), "abstained": r.get("abstained")}   # the recorded v3 answer
            for q in simulated_queries(r["question"]):
                urllib.request.urlopen(f"{base_url}/m/{tok}/search?q={urllib.parse.quote_plus(q)}", timeout=120).read()
            final = {"answer": None, "abstained": None, "cited": []}
            searches = [{"q": s["q"], "hits": s["hits"]} for s in memory.requests_for(tok)]
            status = "simulated"
        else:
            rh = histories.get(r["history_id"]) or new_history()
            histories[r["history_id"]] = rh
            out = run_one({**r, "question_id": qid}, split, base_url, rh, a.timeout)
            first, final, searches, status = out["first"], out["final"], out["searches"], "reactor"
            if searches and out["res"].get("status") == "answered":
                with open(OUT, "a", encoding="utf-8") as f:
                    f.write(json.dumps({**out["res"], "question_id": qid, "dataset_history": r["history_id"],
                                        "history_id": rh, "askback": True, "searches": len(searches)}) + "\n")
        demo[qid] = {"status": status, "question": r["question"], "first": first, "searches": searches,
                     "final": final, "latency_s": None if a.dry_run else round(time.time() - t0, 1)}
        DEMO.write_text(json.dumps(demo, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[{n}/{len(qids)}] {qid} {status} searches={len(searches)} "
              f"first={first.get('answer')!r} final={final.get('answer')!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
