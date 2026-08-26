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
    """Draft name -> feed entry. Exact first (feeds also key their table by ESPN's location,
    so 'Texas' lands on the Longhorns rather than Texas A&M), then a loose match only when it
    is unambiguous. The old 'same last word' rule is gone: it paired Newcastle United with
    Leeds United, and plain substring made every Texas school look like the same team."""
    for cand in (team, ALIAS.get(team, team)):
        if cand in table:
            return table[cand]
    t = ALIAS.get(team, team).lower()
    hits = {rank for name, rank in table.items() if (n := name.lower()) and (t in n or n in t)}
    return hits.pop() if len(hits) == 1 else None

def build(picks_path="data/picks.json", overrides_path="data/overrides.json"):
    P, O = load(picks_path), load(overrides_path)
    drafters, picks = P["drafters"], P["picks"]
    N = len(drafters)
    out = {"generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
           "season": P["season"], "drafters": drafters, "sports": {}}
    totals = {d: {"inplay": 0, "confirmed": 0, "bonus": 0, "scored": 0} for d in drafters}
    draft_order = P.get("draft_order", {})
    for key, (name, feed_id, window, note, start) in SPORTS.items():
        table, winners, source = comp_order(key, feed_id, O)
        drafter_of = {picks[d][key]: d for d in drafters}
        ranks = {d: (match(picks[d][key], table) if table else None) for d in drafters}
        pts, bon = rank_points(N, ranks), bonus_points(key, winners, drafter_of)
        taken = draft_order.get(key, {})
        rows = []
        for d in drafters:
            p = pts[d]
            rows.append({"drafter": d, "pick": picks[d][key], "rank": ranks[d], "points": p,
                         "bonus": bon.get(d, 0), "drafted": taken.get(d)})
            if p is not None:
                bucket = "confirmed" if source == "confirmed" else "inplay"
                totals[d][bucket] += p + bon.get(d, 0); totals[d]["bonus"] += bon.get(d, 0); totals[d]["scored"] += 1
        out["sports"][key] = {"name": name, "window": window, "note": note, "source": source, "start": start,
                              "rows": sorted(rows, key=lambda r: (r["points"] is None, -(r["points"] or 0)))}
    for d in drafters:
        totals[d]["total"] = totals[d]["inplay"] + totals[d]["confirmed"]
    order = sorted(drafters, key=lambda d: (-totals[d]["total"], -totals[d]["confirmed"]))
    out["ladder"] = [{"pos": i + 1, "drafter": d, **totals[d]} for i, d in enumerate(order)]
    return out

def resolve_pick(pick, team_list):
    """Draft name -> exactly one ESPN team, or None. Exact display name wins, then ESPN's
    location ('Texas' is the Longhorns; 'Texas A&M' and 'North Texas' are different schools),
    then a loose match only when it is unique across the whole competition."""
    want = ALIAS.get(pick, pick)
    lw = want.lower()
    for display, loc in team_list:
        if display.lower() == lw or loc.lower() == lw:
            return display
    loose = [d for d, loc in team_list
             if lw in d.lower() or lw in loc.lower() or d.lower() in lw or (loc and loc.lower() in lw)]
    return loose[0] if len(loose) == 1 else None

def match_side(team, side):
    """Match a draft name to one side of a fixture. Much stricter than match(): a fixture has
    only two teams, so loose rules do real damage — 'same last word' paired Newcastle United
    with Leeds United, and plain substring made Texas match Texas A&M, North Texas and Texas
    Tech. Exact on the display name or ESPN's location, else a containment match only when
    exactly one side qualifies."""
    for cand in (team, ALIAS.get(team, team)):
        if cand in side:
            return side[cand]
    t = ALIAS.get(team, team).lower()
    hits = {where for name, where in side.items()
            if (n := name.lower()) == t or t in n.split(" (")[0].split() or n in t}
    return hits.pop() if len(hits) == 1 else None

def build_fixtures(picks_path="data/picks.json", days=21):
    """Next games for every drafted team, with the opponent's owner attached so each drafter
    can see who they are up against. Head-to-head competitions only — racing and the per-event
    sports have no fixtures to show."""
    P = load(picks_path)
    drafters, picks = P["drafters"], P["picks"]
    out = {"generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
           "days": days, "sports": {}}
    for key, (name, feed_id, window, note, start) in SPORTS.items():
        kind, _, arg = feed_id.partition(":")
        if kind != "espn" or arg.startswith("racing"):
            continue
        espn = importlib.import_module("feeds.espn")
        try:
            games = espn.fixtures(arg, days)
            team_list = espn.teams(arg)
        except Exception as e:
            out["sports"][key] = {"name": name, "error": f"{type(e).__name__}: {e}", "games": []}
            continue
        # one canonical team per drafter, decided against the full competition, not per fixture
        owner_of = {}
        for d in drafters:
            pick = picks[d].get(key)
            resolved = resolve_pick(pick, team_list) if pick else None
            if resolved:
                owner_of.setdefault(resolved, d)
        rows = []
        for g in games:
            owner = {"home": owner_of.get(g["home"]), "away": owner_of.get(g["away"])}
            if owner["home"] or owner["away"]:       # only games a drafted team is playing in
                rows.append({"d": g["date"], "h": g["home"], "a": g["away"],
                             "hd": owner["home"], "ad": owner["away"]})
        out["sports"][key] = {"name": name, "games": rows}
    return out

def log_history(res, path="docs/history.json"):
    """One compact ladder snapshot per day, so charts can show movement over the season.
    Re-running on the same day replaces that day's entry rather than adding a duplicate."""
    try:
        with open(path) as f:
            hist = json.load(f)
    except (OSError, ValueError):
        hist = {"entries": []}
    day = res["generated"][:10]
    entry = {"date": day, "ladder": [{"d": r["drafter"], "t": r["total"], "c": r["confirmed"], "p": r["pos"]}
                                     for r in res["ladder"]]}
    hist["entries"] = sorted([e for e in hist["entries"] if e.get("date") != day] + [entry],
                             key=lambda e: e["date"])
    with open(path, "w") as f:
        json.dump(hist, f, separators=(",", ":"))
    return len(hist["entries"])

if __name__ == "__main__":
    res = build()
    json.dump(res, open("docs/standings.json", "w"), indent=1)
    days = log_history(res)
    try:
        fx = build_fixtures()
        json.dump(fx, open("docs/fixtures.json", "w"), separators=(",", ":"))
        nfx = sum(len(s["games"]) for s in fx["sports"].values())
    except Exception as e:
        nfx = f"failed ({type(e).__name__})"
    for r in res["ladder"]:
        print(f"{r['pos']:>2} {r['drafter']:<11} total {r['total']:>3}  confirmed {r['confirmed']:>3}  in play {r['inplay']:>3}  bonus {r['bonus']}  ({r['scored']}/20 sports scoring)")
    print("sources:", {k: v["source"] for k, v in res["sports"].items() if not v["source"].startswith("awaiting")})
    print(f"history: {days} day(s) logged")
    print(f"fixtures: {nfx} upcoming games with a drafted team")
