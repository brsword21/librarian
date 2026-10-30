"""print full turns: python s03_turns.py <split> <hid> <sess_idx>[:<turn_idx>] ...  (prints the turn and the previous one)"""
import sys
sys.path.insert(0, '.')
from core.data import history
split, hid = sys.argv[1:3]
h = history(split, hid)
for spec in sys.argv[3:]:
    si, _, ti = spec.partition(':')
    s = h['sessions'][int(si)]
    print(f"===== sess {si} {s['session_id']} {s['date']} ({len(s['turns'])} turns)")
    rng = range(len(s['turns'])) if not ti else range(max(0, int(ti) - 1), int(ti) + 1)
    for i in rng:
        t = s['turns'][i]
        print(f"  [t{i} {t['role']}] {t['content'][:700]}")
