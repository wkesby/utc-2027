"""ESPN public standings (site.web.api.espn.com). Returns {team display name: rank}, 1 = best.
site.api.espn.com refuses API traffic (403 from the CDN for any client) — site.web.api.espn.com
serves the same JSON. Soccer and racing tables carry an explicit rank; US leagues are ordered
by win% with playoff seed as the tie-break. College football has no winPercent stat, so win%
falls back to the overall W-L record. MLB's 'points' stat is games-back, not table points —
championship points are only trusted for racing (championshipPts).
"""
import json, datetime, urllib.request

def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "utc-scoreboard/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def _entries(node, out):
    """Walk ESPN's nested 'children' groups and collect every standings entry."""
    if isinstance(node, dict):
        for e in node.get("standings", {}).get("entries", []):
            out.append(e)
        for c in node.get("children", []):
            _entries(c, out)
    elif isinstance(node, list):
        for c in node:
            _entries(c, out)
    return out

def _stat(entry, *names):
    for s in entry.get("stats", []):
        if s.get("name") in names or s.get("abbreviation") in names:
            return s.get("value")
    return None

def _record_winpct(entry):
    """Win% from the overall 'W-L' or 'W-L-T' record string; 0.0 before any games."""
    for s in entry.get("stats", []):
        if s.get("name") == "overall":
            try:
                n = [int(x) for x in (s.get("displayValue") or s.get("summary") or "").split("-")]
            except ValueError:
                return None
            games = sum(n)
            if len(n) < 2 or games == 0:
                return 0.0
            return (n[0] + 0.5 * (n[2] if len(n) > 2 else 0)) / games
    return None

def standings(path):
    """path like 'soccer/eng.1' or 'football/nfl@2026' — @year pins the comp's season.
    Without the pin ESPN serves whatever it calls current, which off-season means last
    season's table (NBA/NHL/UCL) or the wrong championship entirely (F1). Returns {} until
    the pinned season exists and someone has actually played, so the page shows 'awaiting'
    instead of an alphabetical placeholder ladder."""
    path, _, season = path.partition("@")
    params = []
    if season:
        params.append(f"season={season}")
    if path.split("/")[0] in ("football", "basketball", "hockey", "baseball"):
        params.append("seasontype=2")   # regular season only — preseason results don't count
    url = f"https://site.web.api.espn.com/apis/v2/sports/{path}/standings"
    if params:
        url += "?" + "&".join(params)
    data = _get(url)
    year = data.get("season", {}).get("year")
    if season and year and str(year) != season:
        return {}
    rows, started = [], False
    for e in _entries(data, []):
        name = e.get("team", {}).get("displayName") or e.get("athlete", {}).get("displayName")
        if not name:
            continue
        rank = _stat(e, "rank")
        winpct = _stat(e, "winPercent", "winPercentage")
        if winpct is None:
            winpct = _record_winpct(e)
        seed = _stat(e, "playoffSeed")
        pts = _stat(e, "championshipPts")
        played = _stat(e, "gamesPlayed") or (_stat(e, "wins") or 0) + (_stat(e, "losses") or 0)
        started = started or bool(played) or bool(pts)
        rows.append((name, rank, winpct, seed, pts))
    if not started:
        return {}
    if rows and all(r[1] is not None for r in rows):
        return {n: int(r) for n, r, *_ in rows}
    if any(r[2] is not None for r in rows):
        key = lambda r: (-(r[2] or 0), r[3] if (r[3] or 0) > 0 else 999)
    else:
        key = lambda r: (-(r[4] or 0),)
    ordered = sorted(rows, key=key)
    out, last, rank = {}, None, 0
    for i, r in enumerate(ordered):
        v = key(r)
        if v != last:
            rank = i + 1; last = v
        out[r[0]] = rank
    return out


def fixtures(path, days=10):
    """Upcoming games for a competition: [{date, home, away}], soonest first.
    Preseason events are dropped so the look-ahead matches what actually scores."""
    path, _, season = path.partition("@")
    today = datetime.date.today()
    rng = f"{today:%Y%m%d}-{today + datetime.timedelta(days=days):%Y%m%d}"
    data = _get(f"https://site.web.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={rng}")
    out = []
    for e in data.get("events", []):
        s = e.get("season") or {}
        if s.get("type") == 1:                       # preseason never scores
            continue
        if season and s.get("year") and str(s["year"]) != season:
            continue                                 # a different season to the one this comp scores
        comp = (e.get("competitions") or [{}])[0]
        if comp.get("status", {}).get("type", {}).get("completed"):
            continue
        home = away = None
        for c in comp.get("competitors", []):
            nm = c.get("team", {}).get("displayName")
            if c.get("homeAway") == "home": home = nm
            elif c.get("homeAway") == "away": away = nm
        if home and away and e.get("date"):
            out.append({"date": e["date"], "home": home, "away": away})
    return sorted(out, key=lambda g: g["date"])
