"""Join Reactor results with the pack file they were asked from and list what needs a look, per route.

    python -m harness.reactor_monitor --results runs/final/v1_results.jsonl --packs runs/final/v3_test_packs.jsonl
Lists (1) INSUFFICIENT_EVIDENCE answers, (2) answers whose citations are not all in cite_plan (decoy or context cited),
(3) uncited answers, and whether each answer is stale (asked from a pack whose hash differs from --packs).
Read-only: never calls Reactor.
"""
from __future__ import annotations

import argparse
import collections
import json


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="runs/final/v1_results.jsonl")
    ap.add_argument("--packs", default="runs/final/v3_test_packs.jsonl")
    a = ap.parse_args(argv)
    packs = {r["question_id"]: r for r in map(json.loads, open(a.packs, encoding="utf-8"))}
    res = {}
    for r in map(json.loads, open(a.results, encoding="utf-8")):
        if r.get("status") == "answered":
            res[r["question_id"]] = r
    by = collections.Counter()
    print(f"{len(res)} answered of {len(packs)} packs")
    for qid, r in res.items():
        p = packs.get(qid)
        if p is None:
            continue
        stale = r.get("pack_hash") != p.get("pack_hash")
        cited = [c.get("id") for c in r.get("citations") or []]
        plan = set(p.get("cite_plan") or [x["id"] for x in p["passages"]])
        tags = []
        if r.get("abstained") or "INSUFFICIENT_EVIDENCE" in (r.get("answer") or ""):
            tags.append("INSUFFICIENT")
        if cited and any(c not in plan for c in cited):
            tags.append("cites-outside-plan")
        if not cited and not r.get("abstained"):
            tags.append("uncited")
        if stale:
            tags.append("STALE(pack changed)")
        by[p.get("route")] += 1
        if tags:
            print(f"{p.get('route', '?'):8s} {qid} {','.join(tags):40s} {(r.get('answer') or '')[:50]!r} "
                  f"| {p['question'][:80]}")
    print("answered per route:", dict(by))


if __name__ == "__main__":
    main()
