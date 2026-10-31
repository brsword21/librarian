"""Warm the hosted backend's caches: run every recorded question's audit search and evidence pack once.
    python3 tools/warm_backend.py [https://librarian67.pages.dev]
"""
import json, sys, time, urllib.request
from pathlib import Path

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://librarian67.pages.dev").rstrip("/")
replay = json.loads((Path(__file__).resolve().parents[1] / "demo" / "replay.json").read_text(encoding="utf-8"))
recs = [("test", r) for r in replay["test"]] + [("dev", r) for r in replay["dev"]]

def post(path, body):
    req = urllib.request.Request(BASE + path, json.dumps(body).encode(), {"content-type": "application/json", "user-agent": "librarian-warmup/1.0"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        r.read()
    return time.time() - t

for n, (split, r) in enumerate(recs, 1):
    try:
        a = post("/api/search", {"split": split, "history_id": r["history_id"], "query": r["question"], "k": 6})
        b = post("/api/pack", {"split": split, "history_id": r["history_id"], "question": r["question"]}) if split == "test" else 0
        print(f"[{n}/{len(recs)}] {a:.1f}s {b:.1f}s {r['question'][:60]}", flush=True)
    except Exception as e:
        print(f"[{n}/{len(recs)}] error {e!r}", flush=True)
