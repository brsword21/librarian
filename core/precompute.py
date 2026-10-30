"""Fill the embedding cache ahead of the sweeps:  python -m core.precompute test dev dev200 [--roles user]"""
from __future__ import annotations

import sys
import time

from core import models
from core.data import history, questions
from core.units import build_units


def run(split: str, roles: set[str] | None = None) -> None:
    hids = list(dict.fromkeys(q.history_id for q in questions(split)))
    seen: set[str] = set()
    t0, sent = time.time(), 0
    for n, hid in enumerate(hids, 1):
        units, _ = build_units(history(split, hid))
        texts = [u.index_text for u in units if (roles is None or u.role in roles)]
        texts = [t for t in dict.fromkeys(texts) if t not in seen]
        seen.update(texts)
        for i in range(0, len(texts), 1024):
            models.embed(texts[i:i + 1024])
        sent += len(texts)
        if n % 10 == 0 or n == len(hids):
            el = time.time() - t0
            print(f"{split}: {n}/{len(hids)} histories, {sent} texts, {el/60:.1f} min", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    roles = None
    if "--roles" in args:
        i = args.index("--roles")
        roles = set(args[i + 1].split(","))
        args = args[:i] + args[i + 2:]
    for s in args:
        run(s, roles)
