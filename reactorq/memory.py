"""Memory search that Reactor itself can call: one user's archive behind an unguessable per-question URL.

Reactor's only tool is "open a web page". We expose our own retrieval (BM25 + bge + cross-encoder, the same index the
lenses use) as a plain-text page, scoped to ONE dataset history through a token, so Reactor can run follow-up searches
in the user's memory when our evidence pack is not enough. Nothing leaves the archive except what Reactor asks for.

    GET /m/<token>/search?q=<words>[&k=5]     plain-text hits: [session id | date] + the matching turns
Every request is logged (runs/askback/log.jsonl), so the ask-back runner knows exactly what Reactor read.
"""
from __future__ import annotations

import json
import secrets
import threading
import time
from pathlib import Path

import core.paths  # noqa: F401
from core.paths import RUNS

DIR = RUNS / "askback"
TOKENS = DIR / "tokens.json"
LOG = DIR / "log.jsonl"
_lock = threading.Lock()


def new_token(split: str, history_id: str, question_id: str) -> str:
    """Register a fresh token for one question (one dataset history); returns it."""
    DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        reg = json.loads(TOKENS.read_text()) if TOKENS.exists() else {}
        tok = secrets.token_urlsafe(9).replace("-", "x").replace("_", "y")
        reg[tok] = {"split": split, "history_id": history_id, "question_id": question_id, "created": time.time()}
        TOKENS.write_text(json.dumps(reg, indent=1))
    return tok


def lookup(token: str) -> dict | None:
    if not TOKENS.exists():
        return None
    return json.loads(TOKENS.read_text()).get(token)


def log_request(token: str, query: str, hits: list[dict], agent: str = "") -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    with _lock, open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"token": token, "t": time.time(), "q": query, "agent": agent[:120],
                            "hits": hits}, ensure_ascii=False) + "\n")


def requests_for(token: str) -> list[dict]:
    if not LOG.exists():
        return []
    out = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r["token"] == token:
                out.append(r)
    return out


def search(split: str, history_id: str, query: str, k: int = 5, pool: int = 60, max_chars: int = 1400) -> list[dict]:
    """Top-k sessions for a free-text query: hybrid retrieval, cross-encoder rerank, best chunk +-1 turn per session."""
    from core.index import HistoryIndex
    from core.pack import render
    hx = HistoryIndex.load(split, history_id)
    query = " ".join(query.split())[:300]
    if not query:
        return []
    cand = [i for i, _ in hx.hybrid(query, k=pool)]
    ranked = hx.rerank(query, cand) if cand else []
    best: dict[str, tuple[int, float]] = {}
    for uid, s in ranked:
        sid = hx.units[uid].session_id
        if sid not in best:
            best[sid] = (uid, s)
        if len(best) >= k:
            break
    hits = []
    for sid, (uid, s) in best.items():
        text, _ = render(hx, hx.neighbors(uid, 1, 1))
        u = hx.units[uid]
        hits.append({"id": sid, "date": u.date_str, "score": round(s, 2),
                     "text": text if len(text) <= max_chars else text[:max_chars].rsplit(" ", 1)[0] + " [...]"})
    hits.sort(key=lambda h: h["date"])  # chronological: the reader sees order and recency
    return hits


def as_text(query: str, hits: list[dict]) -> str:
    if not hits:
        return f'No passages in this user\'s chat archive match "{query}". Try other words, or conclude it is not there.\n'
    lines = [f'{len(hits)} passages from this user\'s chat archive for "{query}" (oldest first). '
             "Each starts with [session id | session date].", ""]
    for h in hits:
        lines += [f"[{h['id']} | {h['date']}]", h["text"], ""]
    return "\n".join(lines)


def help_text(base: str) -> str:
    return ("This is the private chat archive of one user (their past conversations with an assistant).\n"
            f"Search it: {base}/search?q=<a few words>   e.g. {base}/search?q=dog+name\n"
            "Results are plain text: [session id | date] followed by the matching user/assistant turns.\n")
