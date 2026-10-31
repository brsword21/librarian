"""Reactor calibration on dev: a fixed stratified sample, and scoring of Reactor results against dev gold.

    python -m reactorq.calibrate sample --split dev --per-type 8 --abstain 6 > runs/reactor/e1_qids.txt
    python -m reactorq.build_packs --split dev --qids "$(paste -sd, runs/reactor/e1_qids.txt)" --out runs/reactor/e1_packs.jsonl
    python -m reactorq.queue --packs runs/reactor/e1_packs.jsonl --out runs/reactor/e1_results.jsonl
    python -m reactorq.calibrate score --split dev --packs runs/reactor/e1_packs.jsonl --results runs/reactor/e1_results.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import core.paths  # noqa: F401  (puts the upstream kit on sys.path)
from score import score_question, summarize  # upstream kit

from core.data import gold, questions, read_jsonl, session_ids_file
from core.paths import KIT, SPLIT_DIRS
from core.types import SHORT


def sample(split: str, per_type: int, n_abstain: int, seed: int = 7) -> list[str]:
    g = gold(split)
    by = defaultdict(list)
    for q in questions(split):
        gg = g[q.question_id]
        by["abstain" if gg["abstain"] else SHORT[gg["question_type"]]].append(q.question_id)
    r = random.Random(seed)
    out = []
    for k, ids in sorted(by.items()):
        out += r.sample(ids, min(len(ids), n_abstain if k == "abstain" else per_type))
    return out


def score(split: str, packs: Path, results: Path) -> None:
    g = gold(split)
    best = {}
    for r in read_jsonl(results):
        if r.get("status") == "answered" or best.get(r["question_id"], {}).get("status") != "answered":
            best[r["question_id"]] = r
    with tempfile.TemporaryDirectory() as tmp:
        res = Path(tmp) / "r.jsonl"
        res.write_text("".join(json.dumps(r) + "\n" for r in best.values()))
        pred = Path(tmp) / "p.jsonl"
        subprocess.run([sys.executable, str(KIT / "reactor" / "predictions.py"), str(res), "--histories",
                        str(session_ids_file(split)), "--out", str(pred), "--abstain-on",
                        "agent,no-answer"], capture_output=True)
        preds = {p["question_id"]: p for p in read_jsonl(pred)}
    pk = {p["question_id"]: p for p in read_jsonl(packs)}
    rows = []
    for qid in best:
        sq = score_question(preds.get(qid), g[qid])
        sq["route"] = pk.get(qid, {}).get("route")
        sq["latency"] = best[qid].get("latency_s") or best[qid].get("wall_s")
        sq["status"] = best[qid].get("status")
        rows.append(sq)
        p = preds.get(qid, {})
        mark = "OK " if sq["answer"] == "correct" else ("?? " if sq["answer"] == "unjudged" else "XX ")
        print(f"{mark}[{SHORT[g[qid]['question_type']]:8s}{' ABS' if g[qid]['abstain'] else '    '}] "
              f"F1={sq['evidence_f1'] if sq['evidence_f1'] is not None else '-'!s:5.5} "
              f"pred={'ABSTAIN' if p.get('abstain') else (p.get('answer') or '')[:70]!r} | gold={g[qid]['answer'][:60]!r}")
    print()
    tab = summarize(rows)
    cols = ("n", "correct", "unjudged", "abstention_n", "abstention_recall", "false_abstention", "evidence_f1")
    print(f"{'type':26s} " + " ".join(f"{c:>9.9s}" for c in cols))
    for name, row in tab.items():
        print(f"{name:26s} " + " ".join(f"{('-' if row[c] is None else (f'{row[c]:.3f}' if isinstance(row[c], float) else row[c])):>9}" for c in cols))
    lat = sorted(x["latency"] for x in rows if x["latency"])
    if lat:
        print(f"latency: median {lat[len(lat)//2]:.0f}s p90 {lat[int(.9*(len(lat)-1))]:.0f}s; statuses: "
              f"{ {s: sum(1 for x in rows if x['status']==s) for s in set(x['status'] for x in rows)} }")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sample", "score"])
    ap.add_argument("--split", default="dev")
    ap.add_argument("--per-type", type=int, default=8)
    ap.add_argument("--abstain", type=int, default=6)
    ap.add_argument("--packs")
    ap.add_argument("--results")
    a = ap.parse_args()
    if a.cmd == "sample":
        print("\n".join(sample(a.split, a.per_type, a.abstain)))
    else:
        score(a.split, Path(a.packs), Path(a.results))
