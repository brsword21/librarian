"""Ask Reactor every pack, one at a time, one Reactor history per dataset history. Resumable; answers are cached by
pack hash so re-runs and delta runs only ask what changed.

    python -m reactorq.queue --packs runs/final/test_packs.jsonl --out runs/final/results.jsonl [--timeout 240] [--limit N]
Needs ../reactor.env filled and the key in the keychain (see ../CONTEXT.md); calls ../reactor.sh.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from collections import OrderedDict
from pathlib import Path

from core.paths import BASE, CACHE

REACTOR = BASE / "reactor.sh"
CACHE_FILE = CACHE / "reactor_answers.jsonl"


def call(*args: str, timeout: float) -> dict:
    proc = subprocess.run([str(REACTOR), *args, "--timeout", str(int(timeout))], capture_output=True, text=True,
                          encoding="utf-8")
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"status": "error", "error": (proc.stderr or proc.stdout).strip()[-800:]}


def load_cache() -> dict[str, dict]:
    out = {}
    if CACHE_FILE.exists():
        for line in CACHE_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("status") == "answered":
                    out[r["pack_hash"]] = r
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=240)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--max-chars", default="32000")
    a = ap.parse_args(argv)
    packs = [json.loads(l) for l in open(a.packs, encoding="utf-8") if l.strip()]
    out = Path(a.out)
    done = set()
    if out.exists():
        for l in out.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                if r.get("status") == "answered":
                    done.add(r["question_id"])
    cache = {} if a.no_cache else load_cache()
    groups: "OrderedDict[str, list[dict]]" = OrderedDict()
    for p in packs:
        if p["question_id"] not in done:
            groups.setdefault(p["history_id"], []).append(p)
    todo = sum(len(v) for v in groups.values())
    print(f"{todo} questions in {len(groups)} histories to ask ({len(done)} already answered)", flush=True)
    asked = 0
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a", encoding="utf-8") as fo, open(CACHE_FILE, "a", encoding="utf-8") as fc, \
            tempfile.TemporaryDirectory() as tmp:
        for hid, ps in groups.items():
            rh = None
            for p in ps:
                if a.limit and asked >= a.limit:
                    return 0
                hit = cache.get(p["pack_hash"])
                if hit:
                    res = {**hit, "question_id": p["question_id"], "from_cache": True}
                else:
                    if rh is None:
                        for attempt in range(5):
                            nh = call("--new-history", timeout=120)
                            if nh.get("status") == "history":
                                rh = nh["history_id"]
                                break
                            print(f"new-history failed: {nh}", flush=True)
                            time.sleep(10 * (attempt + 1))
                        if rh is None:
                            return 2
                    ev = Path(tmp) / "evidence.json"
                    ev.write_text(json.dumps([{k: v for k, v in x.items() if v is not None} for x in p["passages"]],
                                             ensure_ascii=False), encoding="utf-8")
                    args = ["--history", rh, "--question", p["question_text"], "--question-date", p["question_date"],
                            "--question-id", p["question_id"], "--max-chars", a.max_chars]
                    if p["passages"]:
                        args += ["--evidence", str(ev)]
                    t0 = time.time()
                    res = call(*args, timeout=a.timeout)
                    for attempt in range(2):  # closed / error / timeout / refused: start a fresh history, ask again
                        if res.get("status") == "answered":
                            break
                        print(f"   retry {p['question_id']} after {res.get('status')} {res.get('code') or ''}", flush=True)
                        time.sleep(5)
                        nh = call("--new-history", timeout=120)
                        if nh.get("status") == "history":
                            rh = nh["history_id"]
                            args[1] = rh
                        res = call(*args, timeout=a.timeout)
                    res.update(question_id=p["question_id"], pack_hash=p["pack_hash"], dataset_history=hid,
                               wall_s=round(time.time() - t0, 1))
                    fc.write(json.dumps(res) + "\n")
                    fc.flush()
                asked += 1
                res.update(route=p.get("route"), lens=p.get("lens"), variant=p.get("variant"))
                fo.write(json.dumps(res) + "\n")
                fo.flush()
                ans = (res.get("answer") or res.get("error") or res.get("code") or "")[:80]
                print(f"[{asked}/{todo}] {p['question_id']} {res.get('status')} {res.get('wall_s', '-')}s {ans!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
