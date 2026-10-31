"""SSA-A round 4: lenses/ssa/a_r4_role.py with the nf0 (impersonal question) rule only, no role-play rule."""
from lenses.ssa.a_r4_role import role_guess as _rg


def role_guess(q, hx) -> float:
    return _rg(q, hx, rp=False)
