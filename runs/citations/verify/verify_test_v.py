"""Run current finalize, proposed rules (finalize_proposed) and the learned model on every test answer so far.
Read-only on project files. Run from librarian/ with .venv/bin/python <this> [results.jsonl]."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import core.paths  # noqa: F401
from score import normalize  # kit
from predictions import convert  # kit/reactor

from reactorq import finalize as CUR
from reactorq import attribution as M

spec = importlib.util.spec_from_file_location("fprop", "/private/tmp/claude-501/-Users-mikolaj/1db5489f-85a5-4e53-963c-621650086fb0/scratchpad/finalize_verified.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

res_path = sys.argv[1] if len(sys.argv) > 1 else "runs/final/v1_results.jsonl"
rows = [json.loads(l) for l in open(res_path) if l.strip()]
best = {}
for r in rows:
    q = r.get("question_id")
    if r.get("status") == "answered" or best.get(q, {}).get("status") != "answered":
        best[q] = r
preds, skipped, notes = convert(list(best.values()), {"agent", "no-answer"}, None)
packs_by_hash, packs_by_q = {}, {}
for f in ["runs/final/v3_test_packs.jsonl", "runs/final/v2_test_packs.jsonl", "runs/final/v1_test_packs.jsonl",
          "runs/final/v1_rebuild_test_packs.jsonl", "runs/final/r1c_test_packs.jsonl", "runs/final/r1s_test_packs.jsonl",
          "runs/final/r1_test_packs.jsonl", "runs/final/v0_test_packs.jsonl"]:
    for p in (json.loads(l) for l in open(f)):
        packs_by_hash.setdefault(p["pack_hash"], p)
        packs_by_q.setdefault(p["question_id"], p)

LAB = re.compile(r"\s*\[\s*E\d+(?:\s*[,;]\s*E\d+)*\s*\]")


def contains_ans(text, ans):
    a = normalize(LAB.sub("", ans))
    return bool(a) and f" {a} " in f" {normalize(text)} "


def comp_source(sid, pack, ans):
    return sid in (pack.get("cite_plan") or []) and M.computed_matches(ans, pack.get("computed"))


out = []
nhash = 0
for p in preds:
    r = best[p["question_id"]]
    pack = packs_by_hash.get(r.get("pack_hash"))
    if pack:
        nhash += 1
    else:
        pack = packs_by_q.get(p["question_id"])
    if p["abstain"]:
        continue
    cur = CUR.attribute(p, pack, True, True)[0]["citations"]
    rul, rnote = R.attribute(p, pack, True, True, reply=r.get("reply") or "")
    rul = rul["citations"]
    mod, mnote = M.attribute(p, pack, r)
    mod_noku, _ = M.attribute(p, pack, r, use_ku_chain=False)
    text = {x["id"]: x["text"] for x in pack["passages"] if x.get("id")}
    ids = [x["id"] for x in pack["passages"] if x.get("id")]
    rec = {"qid": p["question_id"], "route": pack["route"], "q": pack["question"][:90], "answer": p["answer"],
           "own": p["citations"], "plan": pack.get("cite_plan"), "computed": pack.get("computed"),
           "labels": {s: f"E{ids.index(s)+1}" for s in ids}}
    for name, cites in (("cur", cur), ("rules", rul), ("model", mod), ("model_noku", mod_noku)):
        removed = [s for s in p["citations"] if s not in cites]
        added = [s for s in cites if s not in p["citations"]]
        rec[name] = {"added": [{"sid": s, "E": rec["labels"].get(s), "contains": contains_ans(text.get(s, ""), p["answer"]),
                                "comp_src": comp_source(s, pack, p["answer"])} for s in added], "removed": removed}
    rec["rnote"], rec["mnote"] = rnote, mnote
    out.append(rec)

print(f"results rows {len(rows)}, questions {len(best)}, preds {len(preds)}, answered {len(out)}, pack by hash {nhash}")
print("skipped", skipped[:5])
for name in ("cur", "rules", "model", "model_noku"):
    ch = [o for o in out if o[name]["added"] or o[name]["removed"]]
    viol = [(o["qid"], a["E"]) for o in out for a in o[name]["added"] if not a["contains"] and not a["comp_src"]]
    rem = [(o["qid"], o[name]["removed"]) for o in out if o[name]["removed"]]
    print(f"\n== {name}: changed {len(ch)}, sessions added {sum(len(o[name]['added']) for o in out)}, "
          f"not-containing & not-computation-source {len(viol)}, removals {len(rem)}")
    for o in ch:
        print(f"  {o['qid']} [{o['route']}] ans={o['answer'][:50]!r} own={[o['labels'].get(s) for s in o['own']]} "
              f"plan={[o['labels'].get(s) for s in (o['plan'] or [])]} comp={o['computed']}")
        for a in o[name]["added"]:
            print(f"      + {a['E']} {a['sid']} contains={a['contains']} comp_src={a['comp_src']}")
        if o[name]["removed"]:
            print("      - removed", o[name]["removed"])
json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else "/dev/null", "w"), indent=1)
