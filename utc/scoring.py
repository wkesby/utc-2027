"""Turn a competition's order into UTC points for the drafted picks.

Rules (UTC 2027, 11 drafters): the best-finishing drafted pick earns N points, down to 1.
Ties share the higher score and the next score is skipped (the golf/tennis convention in the rules).
Bonus: +2 if a pick wins its competition (+1 per major/slam for golf and women's tennis).
"""
from .sports import PER_EVENT

def rank_points(n_drafters, ranks):
    """ranks: {drafter: rank in the competition (1 = best) or None when unknown} -> {drafter: points or None}"""
    known = sorted(((r, d) for d, r in ranks.items() if r is not None), key=lambda x: x[0])
    pts, i = {}, 0
    while i < len(known):
        j = i
        while j < len(known) and known[j][0] == known[i][0]:
            j += 1
        for k in range(i, j):
            pts[known[k][1]] = n_drafters - i
        i = j
    for d, r in ranks.items():
        if r is None:
            pts[d] = None
    return pts

def bonus_points(sport, winners, drafter_of):
    """winners: competition (or major/slam) winners so far -> {drafter: bonus points}"""
    per = 1 if sport in PER_EVENT else 2
    out = {}
    for w in winners:
        d = drafter_of.get(w)
        if d:
            out[d] = out.get(d, 0) + per
    return out
