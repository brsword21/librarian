"""Compare test cites / pack sizes of two audit runs; print the user lines of changed cites."""
import json, sys, re
A = {r["question"]: r for r in map(json.loads, open(sys.argv[1]))}
B = {r["question"]: r for r in map(json.loads, open(sys.argv[2]))}
np_a = sum(len(r["passages"]) for r in A.values()) / len(A); np_b = sum(len(B[q]["passages"]) for q in A if q in B) / len(A)
print(f"{len(A)} packs; mean passages new={np_a:.2f} old={np_b:.2f}; ap>=0.5 new={sum(r['abstain_p']>=0.5 for r in A.values())} old={sum(B[q]['abstain_p']>=0.5 for q in A if q in B)}")
for q, r in A.items():
    b = B.get(q)
    if not b: continue
    ca, cb = r.get("cite_plan") or [], b.get("cite_plan") or []
    d = r.get("debug", {})
    if ca != cb or len(r["passages"]) != len(b["passages"]):
        print(f"\nQ: {q}\n  new cite={[c[-6:] for c in ca]} np={len(r['passages'])} RU={d.get('runner')} ASST={d.get('asst')}  old cite={[c[-6:] for c in cb]} np={len(b['passages'])}")
        for p in r["passages"]:
            print(f"   {p['id'][-6:]} {p['date'][:10]} {p['text'][:200]!r}")
