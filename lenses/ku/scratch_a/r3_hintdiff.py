"""List test packs whose hint or computed value differs between two test_packs.jsonl files (harness.audit --diff
compares route / cite_plan / passages only)."""
import json, sys, difflib
a = {json.loads(l)["question_id"]: json.loads(l) for l in open(sys.argv[1])}
b = {json.loads(l)["question_id"]: json.loads(l) for l in open(sys.argv[2])}
def hint(r):
    if "hint" in r: return r["hint"] or ""
    qt = r.get("question_text", ""); lines = qt.split("\n")[1:]
    return "\n".join(x for x in lines if not x.startswith("Write the final answer line"))
n = 0
for qid, rb in b.items():
    ra = a.get(qid)
    if ra is None: continue
    ha, hb = hint(ra), hint(rb)
    if ha != hb or ra.get("computed") != rb.get("computed"):
        n += 1
        print(f"== {qid} {rb['question'][:80]} | computed {ra.get('computed')} -> {rb.get('computed')}")
        for d in difflib.unified_diff(ha.split("\n"), hb.split("\n"), lineterm="", n=0):
            if d.startswith(("+", "-")) and not d.startswith(("+++", "---")): print("   ", d[:230])
print(f"{n} of {len(b)} hints/computed changed")
