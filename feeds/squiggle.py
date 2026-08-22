"""AFL ladder from the Squiggle API (free, reliable, asks for a User-Agent). {team: ladder rank}."""
import json, urllib.request, datetime

def standings(year=None):
    year = year or datetime.date.today().year
    req = urllib.request.Request(f"https://api.squiggle.com.au/?q=standings;year={year}",
                                 headers={"User-Agent": "utc-scoreboard/1.0 (private tipping comp)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return {row["name"]: int(row["rank"]) for row in data.get("standings", [])}
