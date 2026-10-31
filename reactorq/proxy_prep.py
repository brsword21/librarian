"""Prepare the simulator experiments (runs on the team machine, which has the embedding caches).

    python -m reactorq.proxy_prep
Writes runs/proxy/packs/exp_<name>_{A,B}.jsonl: the same questions in two variants, only where the packs differ,
at most 40 per experiment, dev200 (test scale) first. A = current v3, B = the alternative.
  notes   temporal route: v3 packs vs the same packs without the code's margin notes (are the notes worth it?)
  multi   multi route: v3 tight packs vs the wider deep8 packs (does breadth help the reader?)
  ssa     ssa route: lens A (quoted recommendation line) vs lens B (whole top session, no quote)
"""
from __future__ import annotations

import json
from pathlib import Path

from core.paths import RUNS
from reactorq.build_packs import pack_hash

P = RUNS / "proxy" / "packs"
SUFFIX = ("Write the final answer line as: only the answer itself (a name, number, date or short phrase), followed by "
          "the [E#] label(s) of the passage(s) that state it. No explanation, no alternatives.")
LIMIT = 40


def load(name: str) -> dict[str, dict]:
    out = {}
    for split in ("dev200", "dev"):
        f = P / f"{name}_{split}.jsonl"
        for line in open(f, encoding="utf-8"):
            p = json.loads(line)
            p["split"] = split
            out.setdefault(p["question_id"], p)   # dev200 first: same question ids as dev, test-scale histories
    return out


def strip_notes(p: dict) -> dict:
    q = dict(p)
    q["question_text"] = f"{p['question']}\n{SUFFIX}"
    q["pack_hash"] = pack_hash(q)
    return q


def write(name: str, pairs: list[tuple[dict, dict]]) -> None:
    pairs = pairs[:LIMIT]
    for tag, idx in (("A", 0), ("B", 1)):
        with open(P / f"exp_{name}_{tag}.jsonl", "w", encoding="utf-8") as f:
            for pr in pairs:
                f.write(json.dumps(pr[idx], ensure_ascii=False) + "\n")
    n200 = sum(1 for a, _ in pairs if a["split"] == "dev200")
    print(f"exp_{name}: {len(pairs)} questions ({n200} dev200, {len(pairs) - n200} dev)")


def main() -> None:
    v3 = load("v3")
    write("notes", [(p, strip_notes(p)) for p in v3.values() if p["route"] == "temporal" and
                    p["question_text"].strip() != f"{p['question']}\n{SUFFIX}".strip()])
    deep = load("multideep8")
    write("multi", [(v3[q], deep[q]) for q in v3 if v3[q]["route"] == "multi" and q in deep
                    and deep[q]["pack_hash"] != v3[q]["pack_hash"]])
    bsem = load("ssabsem")
    write("ssa", [(v3[q], bsem[q]) for q in v3 if v3[q]["route"] == "ssa" and q in bsem
                  and bsem[q]["pack_hash"] != v3[q]["pack_hash"]])


if __name__ == "__main__":
    main()
