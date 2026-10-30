import json, re, sys
sys.path.insert(0, '.')
from core.data import history
Q = [
 ("h_d99a2da8f8ee", r"ceramics (class )?instructor|instructor.*ceramic|ceramics.*taught|teaches.*ceramics"),
 ("h_961be7a385ce", r"job title|my title|promot|position as|work as an?|I'm an? [A-Z]|role as|my role"),
 ("h_961be7a385ce", r"watercolou?r class"),
 ("h_ba495aa00d0c", r"\brent\b"),
 ("h_d98b301f60c5", r"spice.*(from|at) |Spice Souk|Moroccan spices|ras el hanout|saffron"),
 ("h_b1bb331d3d3d", r"long run.*\d|\d.*long run"),
 ("h_dbd495da8ce2", r"Icelandic|Bjørn"),
 ("h_dbd495da8ce2", r"chapters"),
 ("h_712dab179f1b", r"skateboard.*'|named|renamed|calls? (it|my)"),
]
for hid, pat in Q:
    h = history('test', hid)
    rx = re.compile(pat, re.I)
    print('#####', hid, pat)
    for si, s in enumerate(h['sessions']):
        for ti, t in enumerate(s['turns']):
            for sent in re.split(r'(?<=[.!?])\s+', t['content']):
                if rx.search(sent) and len(sent) < 400:
                    print(f"  [{si}] {s['date'][:10]} {t['role'][0]} t{ti}: {sent[:300]}")
