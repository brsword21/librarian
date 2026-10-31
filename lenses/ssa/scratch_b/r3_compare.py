"""Compare b_r3_role variants against v1 per question (route changes, S deltas, hint-guard firings by gold type).
Usage: .venv/bin/python -m lenses.ssa.scratch_b.r3_compare <tag-dir e.g. runs/r3-ssa-b/ssu-routed/b_r3_role> <split>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load(p: Path) -> dict:
    f = p / "per_question.jsonl"
    return {json.loads(x)["question_id"]: json.loads(x) for x in f.read_text().splitlines()} if f.exists() else {}


def main(base: str, split: str):
    b = Path(base)
    v1 = load(b / "v1" / split)
    for var in ("comb", "v1_guard", "comb_guard", "comb_guard_adv"):
        x = load(b / var / split)
        if not x:
            continue
        n = len(v1)
        dS = sum(x[q].get("S", 0) - v1[q].get("S", 0) for q in v1 if q in x and v1[q].get("S") is not None
                 and x[q].get("S") is not None)
        print(f"== {var}: n={n} sum dS={dS:+.1f} (mean {dS / max(1, n):+.2f})")
        for q in v1:
            a, c = v1[q], x.get(q)
            if not c:
                continue
            ch = []
            if a.get("route") != c.get("route"):
                ch.append(f"route {a.get('route')}->{c.get('route')}")
            if (a.get("hint") or "") != (c.get("hint") or ""):
                ch.append("hint")
            if a.get("S") is not None and c.get("S") is not None and abs(a["S"] - c["S"]) > 0.05:
                ch.append(f"S {a['S']:.1f}->{c['S']:.1f}")
            if ch:
                print(f"   {c.get('type', '?')[:14]:14s} {'; '.join(ch):40s} {c['question'][:80]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
