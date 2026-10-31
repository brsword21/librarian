"""Demo server: static frontend + recorded answers + live mode.

    .venv/bin/python -m demo.server --web demo/web --port 8800      # then open http://127.0.0.1:8800
Endpoints:
  GET  /replay.json                      recorded test + dev answers (python -m demo.export_replay refreshes it)
  GET  /api/status                       {"reactor_busy": bool}  (busy while the benchmark queue is running)
  POST /api/pack  {"question_id"} or {"split", "history_id", "question"}  -> the evidence pack (fast, local)
  POST /api/ask   same body                -> pack + Reactor's answer (slow: ~1-2 min; only when Reactor is idle)
  POST /api/upload {"name", "content"} (or the raw file as the body) -> {"history_id", "split": "upload", ...}
                                         any archive (see demo/ingest.py); indexing continues in the background
  GET  /api/uploads                      uploaded archives with their indexing state ("indexing" / "ready" / "error")
  GET  /live                             minimal page: upload an archive, ask it, see the pages and Reactor's answer
  GET  /inbox                            the archive as an inbox + the whole workflow (route, search, notes, Reactor,
                                         output); every live answer is logged and exported
  GET  /api/archive?split=&history_id=   the archive's sessions, newest first: id, date, turns, chars, preview
  GET  /api/session?split=&history_id=&session_id=   one session's turns
  GET  /api/outputs[?history_id=]        live answers logged by /api/ask (newest first; cache/live_outputs.jsonl)
  POST /api/search {"split", "history_id", "query", "k"}   top-k sessions for free text, oldest first
  POST /api/jobs  {"kind": "ask"|"askback", ...pack body}  -> 202 {"job_id"}; GET /api/jobs/<id> polls it
                                         (Reactor runs as a queued job: hosted proxies cut requests at ~100 s)
  GET  /m/<token>/search?q=              plain-text search over ONE archive for the model (reactorq/memory.py)
  GET  /api/log                          container diagnostics (model/server log tails, memory)
Hosted: Cloudflare Container (cloudflare/api) behind librarian67.pages.dev; MCP server at /mcp (cloudflare/functions).
Ask an uploaded archive with {"split": "upload", "history_id": ..., "question": ...}. One Reactor call at a time across
all demo servers on this machine (file lock); a second caller gets 409. API responses allow any origin (CORS).
Needs core.model_server running (for packs) and, for /api/ask, ../reactor.env + the keychain key.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import socket
import subprocess
import tempfile
import threading
import time
import traceback
import uuid
from collections import deque
from datetime import datetime
from urllib.parse import parse_qs, urlparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import core.paths  # noqa: F401
from core.data import DATE_FMT, questions, shard_dir
from core.paths import BASE, CACHE, ROOT
from core.types import Question

SUFFIX = ("Write the final answer line as: only the answer itself (a name, number, date or short phrase), followed by "
          "the [E#] label(s) of the passage(s) that state it. No explanation, no alternatives.")
PIPE = None
UPLOAD_DIR = shard_dir("upload")
UPLOADS: dict[str, dict] = {}          # history_id -> summary + indexing state
REACTOR_LOCK = CACHE / "reactor_demo.lock"
OUTPUTS = CACHE / "live_outputs.jsonl"
MAX_BODY = 40_000_000
ALLOW_REACTOR = os.environ.get("LIBRARIAN_REACTOR") == "1"
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
MAX_QUEUE = 4
JOBS: dict[str, dict] = {}
QUEUE: deque[str] = deque()
COND = threading.Condition()
HEAVY = threading.BoundedSemaphore(int(os.environ.get("LIBRARIAN_HEAVY", "2")))   # pack/search at once


class Busy(Exception):
    pass


def reactor_busy() -> bool:
    # anchored to a python process, so a shell or grep that merely mentions the module does not count
    try:   # no pgrep in the container
        return subprocess.run(["pgrep", "-f", r"^[^ ]*python[^ ]* -m reactorq\.queue"], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def reactor_configured() -> bool:
    if not ((BASE / "reactor.sh").exists() and (BASE / "reactor.env").exists()):
        return False
    if os.environ.get("LIBRARIAN_FAKE_REACTOR") == "1" or os.environ.get("REACTOR_ACCESS_KEY"):
        return True   # tests / hosted container (key arrives as a secret env var)
    try:   # macOS keychain (laptop)
        return subprocess.run(["security", "find-generic-password", "-a", os.environ.get("USER", ""), "-s",
                               "reactor-hackathon-key"], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def models_ok() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 8765), timeout=0.5):
            return True
    except OSError:
        return False


def make_question(body: dict) -> tuple[str, Question]:
    if body.get("question_id"):
        for split in ("test", "dev"):
            for q in questions(split):
                if q.question_id == body["question_id"]:
                    if body.get("question"):  # same history, a different question
                        return split, Question("q_live", q.history_id, body["question"], q.date, q.date_str)
                    return split, q
        raise KeyError(body["question_id"])
    split = body.get("split", "test")
    if split == "upload":
        if not (UPLOAD_DIR / f"{body['history_id']}.json").exists():
            raise KeyError(f"no uploaded archive {body['history_id']}")
        d = datetime.strptime(body["question_date"], DATE_FMT) if body.get("question_date") \
            else datetime.now().replace(second=0, microsecond=0)
        return split, Question("q_live", body["history_id"], body["question"], d, d.strftime(DATE_FMT))
    ref = next(q for q in questions(split) if q.history_id == body["history_id"])
    return split, Question("q_live", ref.history_id, body["question"], ref.date, ref.date_str)


def pack_for(body: dict) -> dict:
    global PIPE
    if PIPE is None:
        from harness.sweep import load_lens   # heavy (bm25s, torch client): only for live packs, so replay runs on bare python3
        PIPE = load_lens("lenses/pipeline.py")
    split, q = make_question(body)
    from core.index import HistoryIndex
    from core.pack import question_text   # needs the organisers' kit next to the repo
    hx = HistoryIndex.load(split, q.history_id)
    t0 = datetime.now()
    pack = PIPE.build(q, hx, config="configs/best.json")
    return {"question_id": q.question_id, "history_id": q.history_id, "question": q.question,
            "question_date": q.date_str, "route": pack.route,
            "notes": pack.hint, "computed": pack.computed, "abstain_p": pack.abstain_p,
            "passages": [{"id": p.id, "date": p.date, "text": p.text} for p in pack.passages],
            "cite_plan": pack.planned_citations(), "build_ms": int((datetime.now() - t0).total_seconds() * 1000),
            "question_text": question_text(q, "\n".join(x for x in (pack.hint, SUFFIX) if x))}


def _reactor(args: list[str]) -> dict:
    r = subprocess.run([str(BASE / "reactor.sh"), *args], capture_output=True, text=True)
    lines = r.stdout.strip().splitlines()
    if r.returncode or not lines:
        raise RuntimeError(f"Reactor client failed (exit {r.returncode}): {(r.stderr or '').strip()[-300:]}")
    return json.loads(lines[-1])


def ask(p: dict) -> dict:
    nh = _reactor(["--new-history"])
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump([{k: v for k, v in x.items() if v is not None} for x in p["passages"]], f, ensure_ascii=False)
    args = ["--history", nh["history_id"], "--question", p["question_text"], "--question-date", p["question_date"],
            "--timeout", "600", "--max-chars", "32000"]
    if p["passages"]:
        args += ["--evidence", f.name]
    r = _reactor(args)
    answer = re.sub(r"\s*\[\s*E\d+(?:\s*[,;]\s*E\d+)*\s*\]", "", r.get("answer") or "").strip()
    return {**p, "status": r.get("status"), "answer": answer, "abstained": bool(r.get("abstained")),
            "cited": [c["id"] for c in r.get("citations") or [] if c.get("id")], "latency_s": r.get("latency_s"),
            "reasoning": (r.get("reply") or "")[:4000]}


def ask_locked(body: dict) -> dict:
    """Pack + Reactor under a machine-wide lock, so two demo servers never talk to Reactor at once."""
    REACTOR_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(REACTOR_LOCK, "w") as lf:
        try:
            fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Busy("Reactor is answering another live question; try again in a minute")
        out = ask(pack_for(body))
    log_output(body, out)
    return out


def log_output(body: dict, out: dict) -> None:
    rec = {"time": datetime.now().strftime(DATE_FMT), "split": body.get("split", "test"),
           "history_id": out["history_id"], "question": out["question"], "question_date": out["question_date"],
           "route": out["route"], "answer": out["answer"], "abstained": out["abstained"], "cited": out["cited"],
           "status": out["status"], "latency_s": out["latency_s"], "computed": out["computed"],
           "passages": [{"id": x["id"], "date": x["date"]} for x in out["passages"]],
           "pack_chars": sum(len(x["text"]) for x in out["passages"])}
    with open(OUTPUTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def outputs(history_id: str | None) -> list[dict]:
    if not OUTPUTS.exists():
        return []
    rows = [json.loads(x) for x in OUTPUTS.read_text(encoding="utf-8").splitlines() if x.strip()]
    return [r for r in rows if not history_id or r["history_id"] == history_id][::-1][:200]


def _hist(split: str, hid: str) -> dict:
    from core.data import history
    if split == "upload" and not (UPLOAD_DIR / f"{hid}.json").exists():
        raise KeyError(f"no uploaded archive {hid}")
    return history(split, hid)


def archive(split: str, hid: str) -> dict:
    h = _hist(split, hid)
    rows = []
    for s in h["sessions"]:
        first = next((t["content"] for t in s["turns"] if t["role"] == "user"), s["turns"][0]["content"] if s["turns"] else "")
        rows.append({"session_id": s["session_id"], "date": s["date"], "turns": len(s["turns"]),
                     "chars": sum(len(t["content"]) for t in s["turns"]), "preview": " ".join(first.split())[:160]})
    rows.sort(key=lambda r: datetime.strptime(r["date"], DATE_FMT), reverse=True)
    return {"split": split, "history_id": hid, "sessions": rows, "chars": sum(r["chars"] for r in rows)}


def session(split: str, hid: str, sid: str) -> dict:
    s = next((s for s in _hist(split, hid)["sessions"] if s["session_id"] == sid), None)
    if s is None:
        raise KeyError(f"no session {sid}")
    return {"session_id": sid, "date": s["date"], "turns": [{"role": t["role"], "content": t["content"]} for t in s["turns"]]}


def _index_upload(hid: str) -> None:
    """Builds BM25 and embeds every unit now, so the first question on a new archive is as fast as on test."""
    st = UPLOADS[hid]
    try:
        from core.index import HistoryIndex
        hx = HistoryIndex.load("upload", hid)
        hx.bm25_scores("warm up")
        uids, step = list(range(len(hx.units))), 256
        st["units"] = len(uids)
        for i in range(0, len(uids), step):
            hx.vectors(uids[i:i + step])
            st["progress"] = round(min(1.0, (i + step) / max(1, len(uids))), 3)
        st["state"] = "ready"
    except Exception as exc:
        st.update(state="error", error=repr(exc))


def upload(raw: str, name: str) -> dict:
    from demo.ingest import to_history
    hist, info = to_history(raw, name)
    hid = hist["history_id"]
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{hid}.json"
    if hid in UPLOADS and UPLOADS[hid]["state"] != "error":
        return {**UPLOADS[hid], "split": "upload"}
    info["uploaded"] = datetime.now().strftime(DATE_FMT)
    path.write_text(json.dumps({**hist, "upload_info": info}, ensure_ascii=False), encoding="utf-8")
    UPLOADS[hid] = {**info, "state": "indexing", "progress": 0.0}
    threading.Thread(target=_index_upload, args=(hid,), daemon=True).start()
    return {**UPLOADS[hid], "split": "upload"}


# ---- Reactor jobs (queued, one at a time, sharing REACTOR_LOCK with /api/ask) ------------------------------------
def reactor_state() -> str:
    if not (ALLOW_REACTOR and reactor_configured()):
        return "disabled"
    running = any(j["status"] == "running" for j in JOBS.values())
    return "busy" if running or reactor_busy() or len(QUEUE) >= MAX_QUEUE else "enabled"


def submit(kind: str, body: dict, base_url: str) -> dict:
    make_question(body)   # validate before queueing
    job = {"job_id": uuid.uuid4().hex[:12], "kind": kind, "body": body, "base_url": base_url, "status": "queued",
           "stage": "queued", "t0": time.time(), "pack": None, "token": None, "result": None, "error": None}
    with COND:
        JOBS[job["job_id"]] = job
        QUEUE.append(job["job_id"])
        COND.notify()
    return job


def run_job(job: dict) -> None:
    from reactorq.askback import new_history, run_one
    job["status"], job["stage"] = "running", "pack"
    split = make_question(job["body"])[0]
    p = {**pack_for(job["body"]), "split": split}
    job["pack"] = {k: v for k, v in p.items() if k != "question_text"}
    REACTOR_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(REACTOR_LOCK, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)   # wait for a running /api/ask
        t0 = time.time()
        rh = new_history()
        out = run_one(p, split, job["base_url"], rh, timeout=600, askback=job["kind"] == "askback",
                      on_stage=lambda s: job.__setitem__("stage", s), on_token=lambda t: job.__setitem__("token", t))
    job["result"] = {**out["final"], "latency_s": round(time.time() - t0, 1),
                     "first": out["first"] if job["kind"] == "askback" else None}
    job["status"], job["stage"], job["t_end"] = "done", "done", time.time()


def worker() -> None:
    while True:
        with COND:
            while not QUEUE:
                COND.wait()
            jid = QUEUE.popleft()
        job = JOBS[jid]
        try:
            run_job(job)
        except Exception as exc:
            job["status"], job["error"], job["t_end"] = "error", repr(exc), time.time()
            traceback.print_exc()


def job_view(job: dict) -> dict:
    from reactorq import memory
    searches = [{"q": s["q"], "hits": s["hits"]} for s in memory.requests_for(job["token"])] if job["token"] else []
    pos = list(QUEUE).index(job["job_id"]) + 1 if job["job_id"] in QUEUE else 0
    return {"job_id": job["job_id"], "kind": job["kind"], "status": job["status"], "stage": job["stage"],
            "position": pos, "elapsed_s": round(job.get("t_end", time.time()) - job["t0"], 1), "pack": job["pack"],
            "searches": searches, "result": job["result"], "error": job["error"]}


def diagnostics() -> str:
    out = []
    try:
        mem = {l.split(":")[0]: l.split(":")[1].strip() for l in open("/proc/meminfo") if l.split(":")[0] in ("MemTotal", "MemAvailable")}
        names = sorted(k for k in os.environ if k.startswith(("REACTOR", "PUBLIC", "OMP", "LIBRARIAN")))
        out.append(f"== memory {mem}\n== env names {names} allow_reactor={ALLOW_REACTOR} configured={reactor_configured()}\n")
    except Exception as exc:
        out.append(f"== diagnostics n/a {exc!r}\n")
    for f in ("/tmp/model.log", "/tmp/server.log"):
        if os.path.exists(f):
            out.append(f"== {f}\n" + "".join(open(f, errors="replace").readlines()[-40:]))
    return "\n".join(out)


class Handler(SimpleHTTPRequestHandler):
    web: Path = ROOT / "demo" / "web"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(self.web), **kw)

    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Filename")
        self.send_header("Access-Control-Allow-Private-Network", "true")   # a hosted page calling this laptop

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, ctype: str):
        data = path.read_bytes()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _text(self, text: str, code=200):
        body = text.encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _public_base(self) -> str:
        return PUBLIC_URL or self.headers.get("X-Public-Origin", "") or f"http://{self.headers.get('Host', '')}"

    def _memory(self):
        """GET /m/<token>[/search?q=..&k=..]: the model's own search over one archive (reactorq/memory.py)."""
        from urllib.parse import urlsplit
        from reactorq import memory
        parts = urlsplit(self.path)
        seg = [x for x in parts.path.split("/") if x]
        reg = memory.lookup(seg[1]) if len(seg) >= 2 else None
        if reg is None:
            return self._text("unknown or expired archive link\n", 404)
        base = f"{self._public_base()}/m/{seg[1]}"
        qs = parse_qs(parts.query)
        query = (qs.get("q") or qs.get("query") or [""])[0]
        if len(seg) == 2 or not query:
            return self._text(memory.help_text(base))
        k = max(1, min(8, int((qs.get("k") or ["5"])[0])))
        with HEAVY:
            hits = memory.search(reg["split"], reg["history_id"], query, k=k)
        memory.log_request(seg[1], query, hits, self.headers.get("User-Agent", ""))
        self._text(memory.as_text(query, hits))

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/replay.json"):
            self._file(ROOT / "demo" / "replay.json", "application/json; charset=utf-8")
        elif self.path.startswith("/api/status"):
            self._json({"reactor_busy": reactor_busy(), "online": True, "models": models_ok(),
                        "reactor": reactor_state(), "queue": len(QUEUE)})
        elif self.path.startswith("/m/"):
            try:
                self._memory()
            except Exception as exc:
                self._text(f"search failed: {exc!r}\n", 500)
        elif self.path.startswith("/api/jobs/"):
            job = JOBS.get(self.path.split("/")[3].split("?")[0])
            self._json(job_view(job) if job else {"error": "unknown job"}, 200 if job else 404)
        elif self.path.startswith("/api/log"):
            self._text(diagnostics() or "no logs\n")
        elif self.path.startswith("/askback.json"):
            self._file(ROOT / "demo" / "askback.json", "application/json; charset=utf-8")
        elif self.path.startswith("/api/uploads"):
            self._json({"uploads": sorted(UPLOADS.values(), key=lambda u: u["uploaded"], reverse=True)})
        elif self.path.rstrip("/") == "/live" or self.path.startswith("/live?"):
            self._file(ROOT / "demo" / "live.html", "text/html; charset=utf-8")
        elif self.path.rstrip("/") == "/inbox" or self.path.startswith("/inbox?"):
            self._file(ROOT / "demo" / "inbox.html", "text/html; charset=utf-8")
        elif self.path.startswith(("/api/archive", "/api/session", "/api/outputs")):
            q = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
            try:
                if self.path.startswith("/api/archive"):
                    self._json(archive(q.get("split", "upload"), q["history_id"]))
                elif self.path.startswith("/api/session"):
                    self._json(session(q.get("split", "upload"), q["history_id"], q["session_id"]))
                else:
                    self._json({"outputs": outputs(q.get("history_id"))})
            except (KeyError, FileNotFoundError) as exc:
                self._json({"error": f"not found: {exc}"}, 404)
        else:
            super().do_GET()

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > MAX_BODY:
                return self._json({"error": f"file too large (limit {MAX_BODY // 1_000_000} MB)"}, 413)
            raw = self.rfile.read(n)
            if self.path.startswith("/api/upload"):
                body = None
                if "json" in (self.headers.get("Content-Type") or ""):
                    try:
                        body = json.loads(raw)
                    except json.JSONDecodeError:
                        body = None
                if isinstance(body, dict) and isinstance(body.get("content"), str):
                    return self._json(upload(body["content"], body.get("name") or "upload"))
                return self._json(upload(raw.decode("utf-8", "replace"), self.headers.get("X-Filename") or "upload"))
            body = json.loads(raw or b"{}")
            if self.path.startswith("/api/pack"):
                with HEAVY:
                    self._json(pack_for(body))
            elif self.path.startswith("/api/search"):
                from reactorq import memory
                split, q = make_question({**body, "question": body.get("query") or body.get("question")})
                k = max(1, min(10, int(body.get("k", 5))))
                with HEAVY:
                    hits = memory.search(split, q.history_id, q.question, k=k)
                self._json({"history_id": q.history_id, "query": q.question, "question_date": q.date_str, "hits": hits})
            elif self.path.startswith("/api/jobs"):
                kind = body.get("kind")
                if kind not in ("ask", "askback"):
                    self._json({"error": "kind must be ask or askback"}, 400)
                elif reactor_state() == "disabled":
                    self._json({"error": "reactor_disabled"}, 403)
                elif len(QUEUE) >= MAX_QUEUE:
                    self._json({"error": "busy"}, 409)
                else:
                    job = submit(kind, body, self._public_base())
                    self._json({"job_id": job["job_id"], "position": len(QUEUE)}, 202)
            elif self.path.startswith("/api/ask"):
                if reactor_busy():
                    self._json({"error": "Reactor is busy with the benchmark run; replay mode only"}, 409)
                else:
                    self._json(ask_locked(body))
            else:
                self._json({"error": "unknown endpoint"}, 404)
        except Busy as exc:
            self._json({"error": str(exc)}, 409)
        except (ValueError, KeyError, StopIteration) as exc:
            self._json({"error": str(exc)}, 400)
        except Exception as exc:
            self._json({"error": repr(exc)}, 500)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="demo/web")
    ap.add_argument("--port", type=int, default=8800)
    ap.add_argument("--host", default="127.0.0.1", help="0.0.0.0 inside the container")
    ap.add_argument("--allow-reactor", action="store_true", help="let queued /api/jobs call Reactor (one at a time)")
    a = ap.parse_args()
    global ALLOW_REACTOR
    ALLOW_REACTOR = ALLOW_REACTOR or a.allow_reactor
    threading.Thread(target=worker, daemon=True).start()
    Handler.web = (ROOT / a.web).resolve()
    if UPLOAD_DIR.exists():   # archives uploaded before a restart: embeddings are cached, so they are ready again
        for f in UPLOAD_DIR.glob("u_*.json"):
            info = json.loads(f.read_text(encoding="utf-8")).get("upload_info") or {"history_id": f.stem, "name": f.stem}
            UPLOADS[f.stem] = {"uploaded": datetime.fromtimestamp(f.stat().st_mtime).strftime(DATE_FMT), **info,
                               "state": "ready", "progress": 1.0}
    print(f"demo on http://{a.host}:{a.port}  (static: {Handler.web}; reactor jobs: "
          f"{'allowed' if ALLOW_REACTOR else 'off'}, configured: {reactor_configured()})", flush=True)
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
