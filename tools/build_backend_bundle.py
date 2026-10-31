"""Bundle what the hosted backend needs into cloudflare/api/bundle/ (the container image copies it).

    .venv/bin/python tools/build_backend_bundle.py
Only the demo's archives: the 15 test users and the dev users that have recorded answers. Their history shards and
the embeddings of every unit and sentence (from cache/models.sqlite), so the container never re-embeds an archive on a
cold start. The organisers' kit is cloned at image build time, not copied here.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import core.paths  # noqa: E402,F401
from core.data import history  # noqa: E402
from core.models import EMB_MODEL, sha  # noqa: E402
from core.paths import CACHE, DATA  # noqa: E402
from core.units import build_units, sentences  # noqa: E402

OUT = ROOT / "cloudflare" / "api" / "bundle"
CODE_EXCLUDE = [".git", ".venv", "cache", "runs", "dist", "cloudflare", "node_modules", "demo/web", "demo/web_*",
                "demo/site/fonts", "lenses/*/scratch_*", "__pycache__", "*.pyc", ".DS_Store", "submission"]


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    lib = OUT / "librarian"
    lib.mkdir(parents=True)
    subprocess.run(["rsync", "-a", *sum((["--exclude", e] for e in CODE_EXCLUDE), []), f"{ROOT}/", f"{lib}/"], check=True)
    replay = json.loads((ROOT / "demo" / "replay.json").read_text(encoding="utf-8"))
    wanted = {"test": sorted({r["history_id"] for r in replay["test"]}),
              "dev": sorted({r["history_id"] for r in replay["dev"]})}
    keys: set[str] = set()
    for split, hids in wanted.items():
        (OUT / "data" / split).mkdir(parents=True)
        shutil.copy(DATA / split / "questions.jsonl", OUT / "data" / split / "questions.jsonl")
        (lib / "cache" / "hist" / split).mkdir(parents=True)
        for hid in hids:
            shutil.copy(CACHE / "hist" / split / f"{hid}.json", lib / "cache" / "hist" / split / f"{hid}.json")
            units, sessions = build_units(history(split, hid))
            for u in units:
                keys.add(sha(EMB_MODEL, u.index_text))
                keys.add(sha(EMB_MODEL, u.text))
                for s in sentences(u.text):
                    keys.add(sha(EMB_MODEL, s))
    src = sqlite3.connect(f"file:{CACHE / 'models.sqlite'}?mode=ro", uri=True)
    dst = sqlite3.connect(lib / "cache" / "models.sqlite")
    dst.execute("CREATE TABLE emb (h TEXT PRIMARY KEY, v BLOB)")
    dst.execute("CREATE TABLE rr (h TEXT PRIMARY KEY, s REAL)")
    ks = sorted(keys)
    found = 0
    for i in range(0, len(ks), 900):
        part = ks[i:i + 900]
        rows = src.execute(f"SELECT h, v FROM emb WHERE h IN ({','.join('?' * len(part))})", part).fetchall()
        dst.executemany("INSERT INTO emb VALUES (?, ?)", rows)
        found += len(rows)
    dst.commit()
    dst.close()
    print(f"bundle: {len(wanted['test'])} test + {len(wanted['dev'])} dev archives, "
          f"{found}/{len(ks)} embeddings cached -> {OUT}")
    subprocess.run(["du", "-sh", str(OUT)])


if __name__ == "__main__":
    main()
