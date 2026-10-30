"""Turn-level gold ("has_answer" flags) recovered from the public LongMemEval oracle file and mapped onto the release's
opaque ids with the release converter's own opaque_id (salt "dev"). Dev splits only; test has no gold.

    python -m core.gold_turns        # writes cache/gold_turns.json and prints the check
"""
from __future__ import annotations

import json
from functools import lru_cache

from core.data import gold, history, questions
from core.paths import CACHE, DATA
from convert_longmemeval import opaque_id  # upstream kit

SALT = "dev"
OUT = CACHE / "gold_turns.json"


def build() -> dict[str, list[str]]:
    recs = json.loads((DATA / "lme" / "longmemeval_oracle.json").read_text(encoding="utf-8"))
    flags: dict[str, list[str]] = {}
    texts: dict[str, str] = {}
    for rec in recs:
        raw = rec["question_id"]
        turns = []
        for sid, sess in zip(rec["haystack_session_ids"], rec["haystack_sessions"]):
            for i, t in enumerate(sess):
                if t.get("has_answer"):
                    tid = opaque_id("t_", f"{sid}:{i}", SALT)
                    turns.append(tid)
                    texts[tid] = t["content"]
        for qid in (opaque_id("q_", raw, SALT), opaque_id("q_", f"{raw}#uncued", SALT)):
            flags[qid] = turns
    # check against the released dev histories: every flagged turn id must exist with identical content
    dev_q = {q.question_id: q for q in questions("dev")}
    found = missing = mismatch = 0
    for qid, tids in flags.items():
        if qid not in dev_q:
            continue
        h = history("dev", dev_q[qid].history_id)
        content = {t["turn_id"]: t["content"] for s in h["sessions"] for t in s["turns"]}
        for tid in tids:
            if tid not in content:
                missing += 1
            elif content[tid] != texts[tid]:
                mismatch += 1
            else:
                found += 1
    known = {q: t for q, t in flags.items() if q in dev_q}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(known), encoding="utf-8")
    g = gold("dev")
    answerable = [q for q in g if not g[q]["abstain"]]
    with_flags = sum(1 for q in answerable if known.get(q))
    print(f"gold turns: {found} matched, {missing} missing, {mismatch} content mismatch; "
          f"{with_flags}/{len(answerable)} answerable dev questions have flagged turns")
    return known


@lru_cache(maxsize=1)
def gold_turns() -> dict[str, list[str]]:
    if not OUT.exists():
        return build()
    return json.loads(OUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    build()
