"""Export recorded Reactor answers + the evidence packs behind them for the demo frontend (replay mode).

    python -m demo.export_replay --out demo/replay.json
One record per question: question, date, route, the code's notes (hint), the passages sent (session id, date, text),
Reactor's answer, which passages it cited, latency, plus the history's session timeline (id + date) so the UI can
draw the whole archive. Dev calibration questions carry the gold answer and evidence for a "was it right" badge.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import core.paths  # noqa: F401
from core.data import gold, history, questions, read_jsonl
from core.paths import RUNS

_SUFFIX = "Write the final answer line as:"


def records(split: str, packs_files: list[Path], results_files: list[Path]) -> list[dict]:
    packs = {}
    for f in packs_files:
        for p in read_jsonl(f):
            packs.setdefault(p["pack_hash"], p)
            packs.setdefault(p["question_id"], p)
    best = {}
    for f in results_files:
        for r in read_jsonl(f):
            if r.get("status") == "answered" or best.get(r.get("question_id"), {}).get("status") != "answered":
                best[r["question_id"]] = r
    g = gold(split)
    qmap = {q.question_id: q for q in questions(split)}
    timelines: dict[str, list] = {}
    out = []
    for qid, r in best.items():
        if r.get("status") != "answered" or qid not in qmap:
            continue
        q = qmap[qid]
        p = packs.get(r.get("pack_hash")) or packs.get(qid)
        if p is None:
            continue
        if q.history_id not in timelines:
            h = history(split, q.history_id)
            timelines[q.history_id] = [{"id": s["session_id"], "date": s["date"],
                                        "title": (s["turns"][0]["content"][:90] if s["turns"] else "")} for s in h["sessions"]]
        hint = p["question_text"][len(q.question):].strip()
        hint = hint.split(_SUFFIX)[0].strip()
        cited = [c["id"] for c in r.get("citations") or [] if c.get("id")]
        answer = re.sub(r"\s*\[\s*E\d+(?:\s*[,;]\s*E\d+)*\s*\]", "", r.get("answer") or "").strip()
        rec = {"question_id": qid, "split": split, "history_id": q.history_id, "question": q.question,
               "question_date": q.date_str, "route": p.get("route"), "notes": hint, "computed": p.get("computed"),
               "passages": p["passages"], "answer": answer, "abstained": bool(r.get("abstained")), "cited": cited,
               "latency_s": r.get("latency_s"), "reasoning": (r.get("reply") or "")[:4000]}
        if qid in g:
            rec["gold"] = {"answer": g[qid]["answer"], "evidence": g[qid]["evidence"], "abstain": g[qid]["abstain"]}
        out.append(rec)
    return out, timelines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="demo/replay.json")
    a = ap.parse_args()
    fin = RUNS / "final"
    test, tl_test = records("test", [fin / "v3_test_packs.jsonl", fin / "v2_test_packs.jsonl", fin / "v1_test_packs.jsonl"],
                           [fin / "v1_results.jsonl"] + sorted(fin.glob("*reask*_results.jsonl")))
    rx = RUNS / "reactor"
    dev, tl_dev = records("dev", [rx / "e1b_packs.jsonl", rx / "e1_packs.jsonl"], [rx / "e1_results.jsonl", rx / "e1b_results.jsonl"])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"test": test, "dev": dev, "timelines": {**tl_test, **tl_dev}}, ensure_ascii=False))
    print(f"{len(test)} test + {len(dev)} dev records, {len(tl_test) + len(tl_dev)} timelines -> {a.out}")


if __name__ == "__main__":
    main()
