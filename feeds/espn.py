"""ESPN public standings (site.web.api.espn.com). Returns {team display name: rank}, 1 = best.
site.api.espn.com refuses API traffic (403 from the CDN for any client) — site.web.api.espn.com
serves the same JSON. Soccer and racing tables carry an explicit rank; US leagues are ordered
by win% with playoff seed as the tie-break. College football is the exception: ESPN only
serves *conference* standings for it, so this module orders it on the AP Top 25 (the poll the
comp follows in season, refreshed weekly on Sunday/Monday US time), with everyone outside the
25 falling in behind on win-loss record and then strength of schedule. MLB's 'points' stat is
games-back, not table points —
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

COLLEGE = "football/college-football"


def _with_locations(table, locs):
    """'Texas' -> Texas Longhorns, distinct from 'Texas A&M' and 'North Texas'.
    Only unambiguous locations are added, so a shared one is never guessed at."""
    for loc, names in locs.items():
        if len(names) == 1 and loc not in table:
            only = next(iter(names))
            if only in table:
                table[loc] = table[only]
    return table


def _record(entry):
    """(wins, losses) from the overall record string, falling back to the W/L stats."""
    for s in entry.get("stats", []):
        if s.get("name") == "overall":
            try:
                n = [int(x) for x in (s.get("displayValue") or s.get("summary") or "").split("-")]
            except ValueError:
                break
            if len(n) >= 2:
                return n[0], n[1]
    w, l = _stat(entry, "wins"), _stat(entry, "losses")
    return int(w or 0), int(l or 0)


def ap_ranks(path, season=""):
    """{team id and name: AP rank} for the current AP Top 25 — the poll this comp follows
    in season. AP refreshes weekly (Sunday/Monday US time), so the table only moves once a
    week, which is the point: it is a merit order, not a win-percentage scramble. Keyed by
    ESPN team id first (exact) with the display name as a fallback key. Returns {} before
    the season's first poll or if the poll can't be read, so the caller can fall back."""
    url = f"https://site.web.api.espn.com/apis/site/v2/sports/{path}/rankings"
    if season:
        url += f"?season={season}"
    try:
        data = _get(url)
    except Exception:
        return {}
    for poll in data.get("rankings") or []:
        blob = f" {poll.get('type', '')} {poll.get('shortName', '')} {poll.get('name', '')} ".lower()
        if not (" ap " in blob or "associated press" in blob):
            continue          # skip the coaches' and playoff-committee polls
        out = {}
        for r in poll.get("ranks") or []:
            t = r.get("team") or {}
            name = t.get("displayName") or " ".join(
                x for x in (t.get("location"), t.get("name")) if x).strip()
            cur = r.get("current")
            if not cur:
                continue
            if t.get("id"):
                out[str(t["id"])] = int(cur)
            if name:
                out.setdefault(name, int(cur))
        if out:
            return out
    return {}


def sos(path, season=""):
    """{team id and name: strength-of-schedule rating}, higher = tougher, from ESPN's FPI.
    Only ever a tie-break behind the record, so any failure just returns {} and equally
    matched teams share a rank instead."""
    url = f"https://site.web.api.espn.com/apis/fitt/v3/sports/{path}/powerindex?limit=300"
    if season:
        url += f"&season={season}"
    try:
        data = _get(url)
    except Exception:
        return {}
    out = {}
    for t in data.get("teams") or []:
        team = t.get("team") or {}
        name = team.get("displayName") or " ".join(
            x for x in (team.get("location"), team.get("name")) if x).strip()
        for cat in t.get("categories") or []:
            names = [str(n).lower() for n in (cat.get("names") or [])]
            values = cat.get("values") or []
            for i, n in enumerate(names):
                if n in ("sos", "strengthofschedule") and i < len(values):
                    try:
                        v = float(values[i])
                    except (TypeError, ValueError):
                        continue
                    if team.get("id"):
                        out[str(team["id"])] = v
                    if name:
                        out.setdefault(name, v)
    return out


def _college_table(path, season, rows, locs):
    """College football, ordered the way the comp actually judges it: the AP Top 25 take
    their poll position, and everyone else falls in behind on win-loss record, then
    strength of schedule. ESPN's standings endpoint can't do this — it serves *conference*
    standings, so every 1-0 team ties on win percentage and the tie-break was the team's
    seed within its own conference, which means nothing across the FBS (it had Texas A&M
    79th in a week they won by 50). Returns {} if the poll can't be read, so the caller
    falls back to the generic ordering."""
    ranked = ap_ranks(path, season)
    if not ranked:
        return {}
    tough = sos(path, season)
    top, rest = {}, []
    for name, _rank, winpct, _seed, _pts, wins, losses, tid in rows:
        ap = ranked.get(tid) or ranked.get(name)
        if ap:
            top[name] = int(ap)
            continue
        rest.append((name, -(winpct or 0.0), -(wins or 0),
                     -(tough.get(tid) or tough.get(name) or 0.0)))
    floor = max(top.values()) if top else 0
    rest.sort(key=lambda r: (r[1], r[2], r[3], r[0]))
    out, last, rank = dict(top), None, floor
    for i, r in enumerate(rest):
        key = r[1:]                       # record first, then strength of schedule
        if key != last:
            rank, last = floor + i + 1, key
        out[r[0]] = rank
    return _with_locations(out, locs)


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
    rows, started, locs = [], False, {}
    for e in _entries(data, []):
        team = e.get("team", {})
        name = team.get("displayName") or e.get("athlete", {}).get("displayName")
        if not name:
            continue
        loc = team.get("location")
        if loc and loc != name:
            locs.setdefault(loc, set()).add(name)
        rank = _stat(e, "rank")
        winpct = _stat(e, "winPercent", "winPercentage")
        if winpct is None:
            winpct = _record_winpct(e)
        seed = _stat(e, "playoffSeed")
        pts = _stat(e, "championshipPts")
        played = _stat(e, "gamesPlayed") or (_stat(e, "wins") or 0) + (_stat(e, "losses") or 0)
        started = started or bool(played) or bool(pts)
        wins, losses = _record(e)
        rows.append((name, rank, winpct, seed, pts, wins, losses, str(team.get("id") or "")))
    if not started:
        return {}
    with_locations = lambda table: _with_locations(table, locs)

    if path == COLLEGE:                 # the AP poll, not ESPN's conference standings
        table = _college_table(path, season, rows, locs)
        if table:
            return table

    if rows and all(r[1] is not None for r in rows):
        return with_locations({n: int(r) for n, r, *_ in rows})
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
    return with_locations(out)


def fixtures(path, days=10, past=0):
    """Games for a competition inside a window: [{date, home, away, ...}], soonest first.
    With past > 0 the window reaches back that many days and finished games are kept, each
    carrying its state ('in'/'post'), score and status line — that is the result history and
    the score fallback the app shows when it can't reach ESPN itself. Every game also carries
    ESPN's event id so a live page can overlay fresher scores onto the same game.
    Preseason events are dropped so the look-ahead matches what actually scores."""
    path, _, season = path.partition("@")
    today = datetime.date.today()
    rng = f"{today - datetime.timedelta(days=past):%Y%m%d}-{today + datetime.timedelta(days=days):%Y%m%d}"
    data = _get(f"https://site.web.api.espn.com/apis/site/v2/sports/{path}/scoreboard?dates={rng}")
    out = []
    for e in data.get("events", []):
        s = e.get("season") or {}
        if s.get("type") == 1:                       # preseason never scores
            continue
        if season and s.get("year") and str(s["year"]) != season:
            continue                                 # a different season to the one this comp scores
        comp = (e.get("competitions") or [{}])[0]
        stype = (comp.get("status") or e.get("status") or {}).get("type", {})
        if stype.get("completed") and not past:      # results only wanted when a window asks for them
            continue
        home = away = None
        hloc = aloc = None
        hs = aws = None
        for c in comp.get("competitors", []):
            team = c.get("team", {})
            nm, loc = team.get("displayName"), team.get("location")
            if c.get("homeAway") == "home": home, hloc, hs = nm, loc, c.get("score")
            elif c.get("homeAway") == "away": away, aloc, aws = nm, loc, c.get("score")
        if home and away and e.get("date"):
            g = {"date": e["date"], "home": home, "away": away,
                 "home_loc": hloc, "away_loc": aloc, "id": e.get("id"),
                 "state": stype.get("state") or "pre"}
            if g["state"] in ("in", "post"):
                g["home_score"], g["away_score"] = hs, aws
                g["detail"] = stype.get("shortDetail") or ""
            out.append(g)
    return sorted(out, key=lambda g: g["date"])


def teams(path):
    """Every team in a competition as (display name, location). Used to resolve a draft
    name to exactly one club before fixtures are matched."""
    path, _, season = path.partition("@")
    url = f"https://site.web.api.espn.com/apis/v2/sports/{path}/standings"
    if season:
        url += f"?season={season}"
    out = []
    for e in _entries(_get(url), []):
        t = e.get("team", {})
        if t.get("displayName"):
            out.append((t["displayName"], t.get("location") or ""))
    return out
