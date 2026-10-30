"""Small per-type sample files for agents to read instead of parsing the full data: runs/samples/<type>.jsonl.

    python -m harness.make_samples
"""
from __future__ import annotations

import json
import re

from core.data import gold, history, questions
from core.gold_turns import gold_turns
from core.paths import RUNS
from core.types import SHORT

TEST_STYLE = {
    "temporal": r"days (apart|after|before)|how long|which came first|ago\b",
    "ssa": r"\byou (recommend|suggest|mention|told)",
    "ku": r"\b(now|current|currently|right now|these days)\b",
    "multi": r"^(how many|how much)|\btotal\b|combined",
    "ssu": r"^(what|which|who|where)\b",
}


def main(n: int = 25) -> None:
    out = RUNS / "samples"
    out.mkdir(parents=True, exist_ok=True)
    g, gt = gold("dev"), gold_turns()
    by_type: dict[str, list] = {s: [] for s in SHORT.values()}
    for q in questions("dev"):
        gg = g[q.question_id]
        bucket = by_type[SHORT[gg["question_type"]]]
        n_abs = sum(1 for x in bucket if x["abstain"])
        if len(bucket) >= n and not (gg["abstain"] and n_abs < 3):
            continue
        h = history("dev", q.history_id)
        sess = {s["session_id"]: s for s in h["sessions"]}
        turns = []
        for s in h["sessions"]:
            for i, t in enumerate(s["turns"]):
                if t["turn_id"] in set(gt.get(q.question_id, [])):
                    prev = s["turns"][i - 1]["content"][-300:] if i else ""
                    turns.append({"session_id": s["session_id"], "date": s["date"], "role": t["role"],
                                  "prev_turn_tail": prev, "text": t["content"][:900]})
        bucket.append({"question_id": q.question_id, "question": q.question, "question_date": q.date_str,
                       "answer": gg["answer"], "abstain": gg["abstain"],
                       "evidence": [{"session_id": e, "date": sess[e]["date"] if e in sess else None} for e in gg["evidence"]],
                       "n_sessions_in_history": len(h["sessions"]), "gold_turns": turns})
    tq = list(questions("test"))
    for short, bucket in by_type.items():
        style = [{"question": q.question, "question_date": q.date_str, "history_id": q.history_id}
                 for q in tq if re.search(TEST_STYLE[short], q.question, re.I)][:15]
        with open(out / f"{short}.jsonl", "w", encoding="utf-8") as f:
            for row in bucket[: n + 3]:
                f.write(json.dumps({"split": "dev", **row}, ensure_ascii=False) + "\n")
            for row in style:
                f.write(json.dumps({"split": "test", **row}, ensure_ascii=False) + "\n")
        print(short, len(bucket[: n + 3]), "dev +", len(style), "test-style")


if __name__ == "__main__":
    main()
