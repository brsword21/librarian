"""Loading questions, gold and histories. Histories are sharded once into one JSON file per history
(cache/hist/<split>/<history_id>.json) so a sweep reads only what it needs.

    python -m core.data shard dev test        # one-off
    python -m core.data dev200                # build the test-scale robustness split from dev-large
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from core.paths import CACHE, DATA, SPLIT_DIRS
from core.types import Question

DATE_FMT = "%Y/%m/%d (%a) %H:%M"


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, DATE_FMT)


def read_jsonl(path: Path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


@lru_cache(maxsize=None)
def questions(split: str) -> tuple[Question, ...]:
    return tuple(Question(q["question_id"], q["history_id"], q["question"], parse_date(q["question_date"]),
                          q["question_date"]) for q in read_jsonl(SPLIT_DIRS[split] / "questions.jsonl"))


@lru_cache(maxsize=None)
def gold(split: str) -> dict[str, dict]:
    path = SPLIT_DIRS[split] / "gold.jsonl"
    return {g["question_id"]: g for g in read_jsonl(path)} if path.exists() else {}


def shard_dir(split: str) -> Path:
    return CACHE / "hist" / split


def shard(split: str) -> int:
    out = shard_dir(split)
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(SPLIT_DIRS[split] / "histories.jsonl", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            head = line[:120]
            hid = head.split('"history_id": "')[1].split('"')[0] if '"history_id": "' in head \
                else json.loads(line)["history_id"]
            (out / f"{hid}.json").write_text(line, encoding="utf-8")
            n += 1
    return n


@lru_cache(maxsize=8)
def history(split: str, history_id: str) -> dict:
    path = shard_dir(split) / f"{history_id}.json"
    if not path.exists():
        shard(split)
    return json.loads(path.read_text(encoding="utf-8"))


def _seed(*parts: str) -> int:
    return int(hashlib.sha1("|".join(parts).encode()).hexdigest()[:12], 16)


def build_dev200(per_type: int = 22, abstain: int = 15, keep: int = 200) -> None:
    """125 dev-large questions (22 answerable per type + 15 unanswerable), each history cut to its gold sessions plus
    random others, `keep` sessions in all (the test's scale), chronological order kept."""
    src = SPLIT_DIRS["dev-large"]
    g = {x["question_id"]: x for x in read_jsonl(src / "gold.jsonl")}
    qs = list(read_jsonl(src / "questions.jsonl"))
    rnd = random.Random(1234)
    rnd.shuffle(qs)
    picked, count = [], defaultdict(int)
    for q in qs:
        gg = g[q["question_id"]]
        key = "abstain" if gg["abstain"] else gg["question_type"]
        if count[key] < (abstain if key == "abstain" else per_type):
            count[key] += 1
            picked.append(q)
    by_hist = defaultdict(list)
    for q in picked:
        by_hist[q["history_id"]].append(q)
    out = SPLIT_DIRS["dev200"]
    out.mkdir(parents=True, exist_ok=True)
    with open(src / "histories.jsonl", encoding="utf-8") as f, \
            open(out / "histories.jsonl", "w", encoding="utf-8") as fh:
        for line in f:
            head = line[:80]
            hid = head.split('"history_id": "')[1].split('"')[0]
            if hid not in by_hist:
                continue
            h = json.loads(line)
            need = {s for q in by_hist[hid] for s in g[q["question_id"]]["evidence"]}
            others = [s["session_id"] for s in h["sessions"] if s["session_id"] not in need]
            r = random.Random(_seed(hid))
            chosen = need | set(r.sample(others, max(0, min(len(others), keep - len(need)))))
            h["sessions"] = [s for s in h["sessions"] if s["session_id"] in chosen]
            fh.write(json.dumps(h, ensure_ascii=False) + "\n")
    with open(out / "questions.jsonl", "w", encoding="utf-8") as fq, open(out / "gold.jsonl", "w", encoding="utf-8") as fg:
        for q in picked:
            fq.write(json.dumps(q, ensure_ascii=False) + "\n")
            fg.write(json.dumps(g[q["question_id"]], ensure_ascii=False) + "\n")
    print(f"dev200: {len(picked)} questions, {len(by_hist)} histories, counts {dict(count)}")


if __name__ == "__main__":
    cmd, *rest = sys.argv[1:]
    if cmd == "shard":
        for s in rest:
            print(s, shard(s), "histories")
    elif cmd == "dev200":
        build_dev200()
        print("dev200", shard("dev200"), "histories sharded")
