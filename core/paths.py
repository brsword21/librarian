"""Where things live. Upstream kit and data sit next to this repo (see README)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]                      # librarian/
BASE = Path(os.environ.get("LIBRARIAN_BASE", ROOT.parent))      # folder holding data/ and memory-challenge/
DATA = BASE / "data"
KIT = BASE / "memory-challenge"
CACHE = ROOT / "cache"
RUNS = ROOT / "runs"

SPLIT_DIRS = {
    "dev": DATA / "dev",
    "dev200": DATA / "dev200",
    "dev-large": DATA / "dev-large",
    "test": DATA / "test",
}

for p in (str(KIT), str(KIT / "reactor")):
    if p not in sys.path:
        sys.path.append(p)
