"""ESPN public standings (site.api.espn.com). Returns {team display name: rank}, 1 = best.
UNTESTED from the build sandbox (no outbound network) — first run on GitHub Actions will prove it.
"""
import json, urllib.request

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

def standings(path):
    """path like 'soccer/eng.1' or 'football/nfl'."""
    data = _get(f"https://site.api.espn.com/apis/v2/sports/{path}/standings")
    entries = _entries(data, [])
    rows = []
    for e in entries:
        name = e.get("team", {}).get("displayName") or e.get("athlete", {}).get("displayName")
        if not name:
            continue
        # soccer tables carry an explicit rank; US leagues are ordered by win% / playoff seed
        rank = _stat(e, "rank")
        winpct = _stat(e, "winPercent", "winPercentage")
        pts = _stat(e, "points", "championshipPts")
        rows.append((name, rank, winpct, pts))
    if all(r[1] is not None for r in rows):
        return {n: int(r) for n, r, _, _ in rows}
    key = (lambda r: -(r[3] or 0)) if any(r[3] for r in rows) else (lambda r: -(r[2] or 0))
    ordered = sorted(rows, key=key)
    out, last, rank = {}, None, 0
    for i, r in enumerate(ordered):
        v = key(r)
        if v != last:
            rank = i + 1; last = v
        out[r[0]] = rank
    return out
