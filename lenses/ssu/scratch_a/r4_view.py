import json, sys
res = {}
for l in open("runs/final/v1_results.jsonl"):
    d = json.loads(l); res[d["question_id"]] = d
for l in open("runs/final/v2_test_packs.jsonl"):
    d = json.loads(l)
    if d["route"] not in ("ssu",) and "ssu" not in d.get("lens", ""):
        continue
    r = res.get(d["question_id"], {})
    hint = d["question_text"].split("\n")[1] if "\n" in d["question_text"] else ""
    print("==", d["question_id"], d["route"], d["variant"], "|", d["question"])
    print("   hint:", hint[:300])
    print("   v1:", r.get("status"), "|", r.get("answer"), "| cites", [c["id"] for c in r.get("citations", [])], "| v1 route", r.get("route"))
    print("   v2 plan:", d.get("cite_plan"), "computed:", d.get("computed"), "abst:", round(float(d.get("abstain_p") or 0),2), "chars", d.get("chars"), "psg", [p["id"] for p in d["passages"]])
