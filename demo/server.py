"""Demo server: static frontend + recorded answers + live mode.

    .venv/bin/python -m demo.server --web demo/web --port 8800      # then open http://127.0.0.1:8800
Endpoints:
  GET  /replay.json                      recorded test + dev answers (python -m demo.export_replay refreshes it)
  GET  /api/status                       {"reactor_busy": bool}  (busy while the benchmark queue is running)
  POST /api/pack  {"question_id"} or {"split", "history_id", "question"}  -> the evidence pack (fast, local)
  POST /api/ask   same body                -> pack + Reactor's answer (slow: ~1-2 min; only when Reactor is idle)
Needs core.model_server running (for packs) and, for /api/ask, ../reactor.env + the keychain key.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import core.paths  # noqa: F401
from core.data import questions
from core.paths import BASE, ROOT
from core.types import Question

SUFFIX = ("Write the final answer line as: only the answer itself (a name, number, date or short phrase), followed by "
          "the [E#] label(s) of the passage(s) that state it. No explanation, no alternatives.")
PIPE = None


def reactor_busy() -> bool:
    return subprocess.run(["pgrep", "-f", "reactorq.queue"], capture_output=True).returncode == 0


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


def ask(p: dict) -> dict:
    sh = str(BASE / "reactor.sh")
    nh = json.loads(subprocess.run([sh, "--new-history"], capture_output=True, text=True).stdout.strip().splitlines()[-1])
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump([{k: v for k, v in x.items() if v is not None} for x in p["passages"]], f, ensure_ascii=False)
    args = [sh, "--history", nh["history_id"], "--question", p["question_text"], "--question-date", p["question_date"],
            "--timeout", "600", "--max-chars", "32000"]
    if p["passages"]:
        args += ["--evidence", f.name]
    r = json.loads(subprocess.run(args, capture_output=True, text=True).stdout.strip().splitlines()[-1])
    answer = re.sub(r"\s*\[\s*E\d+(?:\s*[,;]\s*E\d+)*\s*\]", "", r.get("answer") or "").strip()
    return {**p, "status": r.get("status"), "answer": answer, "abstained": bool(r.get("abstained")),
            "cited": [c["id"] for c in r.get("citations") or [] if c.get("id")], "latency_s": r.get("latency_s"),
            "reasoning": (r.get("reply") or "")[:4000]}


class Handler(SimpleHTTPRequestHandler):
    web: Path = ROOT / "demo" / "web"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(self.web), **kw)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/replay.json"):
            data = (ROOT / "demo" / "replay.json").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path.startswith("/api/status"):
            self._json({"reactor_busy": reactor_busy()})
        else:
            super().do_GET()

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.path.startswith("/api/pack"):
                self._json(pack_for(body))
            elif self.path.startswith("/api/ask"):
                if reactor_busy():
                    self._json({"error": "Reactor is busy with the benchmark run; replay mode only"}, 409)
                else:
                    self._json(ask(pack_for(body)))
            else:
                self._json({"error": "unknown endpoint"}, 404)
        except Exception as exc:
            self._json({"error": repr(exc)}, 500)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="demo/web")
    ap.add_argument("--port", type=int, default=8800)
    a = ap.parse_args()
    Handler.web = (ROOT / a.web).resolve()
    print(f"demo on http://127.0.0.1:{a.port}  (static: {Handler.web})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
