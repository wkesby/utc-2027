"""Feeds -> competition order -> UTC points, split into in-play and confirmed. Writes docs/standings.json."""
import json, datetime, importlib
from .sports import SPORTS
from .scoring import rank_points, bonus_points

def load(path):
    with open(path) as f:
        return json.load(f)

def comp_order(sport, feed_id, overrides):
    """({team: rank}, [winners], source). Confirmed beats overrides beats feeds."""
    winners = overrides.get("bonus", {}).get(sport, [])
    if overrides.get("confirmed", {}).get(sport):
        return overrides["confirmed"][sport], winners, "confirmed"
    if overrides.get("positions", {}).get(sport):
        return overrides["positions"][sport], winners, "override"
    kind, _, arg = feed_id.partition(":")
    if kind == "manual":
        return {}, winners, "awaiting feed"
    try:
        mod = importlib.import_module(f"feeds.{kind}")
        table = mod.standings(arg) if arg else mod.standings()
        return table, winners, f"feed:{kind}" if table else "awaiting feed"
    except Exception as e:
        return {}, winners, f"feed error: {type(e).__name__}: {e}"

ALIAS = {"Man Utd": "Manchester United", "Man City": "Manchester City", "Newcastle Utd": "Newcastle United",
         "Gladbach": "Borussia Mönchengladbach", "LA Rams": "Los Angeles Rams", "LA Chargers": "Los Angeles Chargers",
         "LA Lakers": "Los Angeles Lakers", "LA Clippers": "LA Clippers", "LA Dodgers": "Los Angeles Dodgers",
         "NZ Warriors": "Warriors", "North Qld Cowboys": "North Queensland Cowboys", "Bordeaux Bègles": "Bordeaux-Bègles",
         "Inter Milan": "Internazionale", "PSG": "Paris Saint-Germain", "GWS Giants": "Greater Western Sydney"}

def match(team, table):
    """Loose name match between draft names and feed names."""
    for cand in (team, ALIAS.get(team, team)):
        if cand in table:
            return table[cand]
    t = ALIAS.get(team, team).lower()
    for name, rank in table.items():
        n = name.lower()
        if t in n or n in t or t.split()[-1] == n.split()[-1]:
            return rank
    return None

def build(picks_path="data/picks.json", overrides_path="data/overrides.json"):
    P, O = load(picks_path), load(overrides_path)
    drafters, picks = P["drafters"], P["picks"]
    N = len(drafters)
    out = {"generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
           "season": P["season"], "drafters": drafters, "sports": {}}
    totals = {d: {"inplay": 0, "confirmed": 0, "bonus": 0, "scored": 0} for d in drafters}
    for key, (name, feed_id, window, note) in SPORTS.items():
        table, winners, source = comp_order(key, feed_id, O)
        drafter_of = {picks[d][key]: d for d in drafters}
        ranks = {d: (match(picks[d][key], table) if table else None) for d in drafters}
        pts, bon = rank_points(N, ranks), bonus_points(key, winners, drafter_of)
        rows = []
        for d in drafters:
            p = pts[d]
            rows.append({"drafter": d, "pick": picks[d][key], "rank": ranks[d], "points": p, "bonus": bon.get(d, 0)})
            if p is not None:
                bucket = "confirmed" if source == "confirmed" else "inplay"
                totals[d][bucket] += p + bon.get(d, 0); totals[d]["bonus"] += bon.get(d, 0); totals[d]["scored"] += 1
        out["sports"][key] = {"name": name, "window": window, "note": note, "source": source,
                              "rows": sorted(rows, key=lambda r: (r["points"] is None, -(r["points"] or 0)))}
    for d in drafters:
        totals[d]["total"] = totals[d]["inplay"] + totals[d]["confirmed"]
    order = sorted(drafters, key=lambda d: (-totals[d]["total"], -totals[d]["confirmed"]))
    out["ladder"] = [{"pos": i + 1, "drafter": d, **totals[d]} for i, d in enumerate(order)]
    return out

if __name__ == "__main__":
    res = build()
    json.dump(res, open("docs/standings.json", "w"), indent=1)
    for r in res["ladder"]:
        print(f"{r['pos']:>2} {r['drafter']:<11} total {r['total']:>3}  confirmed {r['confirmed']:>3}  in play {r['inplay']:>3}  bonus {r['bonus']}  ({r['scored']}/20 sports scoring)")
    print("sources:", {k: v["source"] for k, v in res["sports"].items() if not v["source"].startswith("awaiting")})
