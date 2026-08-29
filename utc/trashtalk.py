"""Rubs it in when a drafted team loses to a team nobody wanted: each run scans the fresh
fixtures results for a drafter beaten by an undrafted side, has Claude write the sledge, and
posts it to the banter wall aimed at the loser — the wall's own push pipeline (the instant
Cloud Function, with the 5-minute workflow as safety net) then delivers it to every phone.
A seen-file keeps every defeat to one sledge, no API key falls back to templates, and like
the rest of the notify chain this must never break the workflow that calls it.

    python -m utc.trashtalk
"""
import datetime, json, os, random, urllib.request
from .notify import config, fs

SEEN = "docs/trashtalk.json"
NAME = "The Commentator"     # posts under this name on the wall; no drafter subscribes as it,
                             # so every phone gets the push — the roasted drafter's included
PER_RUN = 3                  # a big weekend drains over the following hourly runs


def beats(fx):
    """Finished games where a drafted team lost to an undrafted one. Head-to-head games are
    the drafters' own fight — the wall handles those without help."""
    out = []
    for s in fx.get("sports", {}).values():
        for g in s.get("games", []):
            if g.get("st") != "post" or bool(g.get("hd")) == bool(g.get("ad")):
                continue
            try:
                hs, aws = float(g["hs"]), float(g["as"])
            except (KeyError, TypeError, ValueError):
                continue
            home = bool(g.get("hd"))
            mine, theirs = (hs, aws) if home else (aws, hs)
            if mine >= theirs:
                continue
            out.append({"id": g.get("i") or f"{g['d']}|{g['h']}|{g['a']}",
                        "drafter": g["hd"] if home else g["ad"],
                        "their_team": g["h"] if home else g["a"],
                        "beaten_by": g["a"] if home else g["h"],
                        "score_for": g["hs"] if home else g["as"],
                        "score_against": g["as"] if home else g["hs"],
                        "competition": s.get("name", "").split(" (")[0]})
    return out


def _claude(b):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = {"model": "claude-opus-5", "max_tokens": 300,
            "system": ("You write one-line trash talk for the banter wall of an 11-mate "
                       "Australian sports tipping comp (the UTC: each drafter picked one team "
                       "per competition). A drafter's team has just been beaten by a team that "
                       "nobody bothered to draft. Reply with the sledge only: one line, plain "
                       "text, under 50 words, PG, Aussie tone, first name only, no emojis, no "
                       "hashtags, no quotes, no preamble. Use only the facts given; never "
                       "invent details."),
            "messages": [{"role": "user", "content": json.dumps(
                {k: b[k] for k in ("drafter", "their_team", "beaten_by",
                                   "score_for", "score_against", "competition")})}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        msg = json.load(r)
    if msg.get("stop_reason") == "refusal":
        return None
    text = " ".join("".join(bl.get("text", "") for bl in msg.get("content", [])
                            if bl.get("type") == "text").split())
    return text or None


def _template(b, rng):
    d, team, opp = b["drafter"], b["their_team"], b["beaten_by"]
    sf, sa, comp = b["score_for"], b["score_against"], b["competition"]
    return rng.choice([
        f"{d}'s {team} just lost {sf}-{sa} to {opp} — a team nobody at the draft even wanted. Says it all really.",
        f"Nobody drafted {opp}. {opp} still beat {d}'s {team} {sa}-{sf}. Sit with that one, {d}.",
        f"{comp} update: {team} {sf}, {opp} {sa}. Beaten by the undrafted mob. Thoughts are with {d} at this time.",
        f"{d} spent a draft pick on {team}. {opp} cost nothing and just beat them {sa}-{sf}. The market has spoken."])


def sledge(b):
    """Claude's line when the key is there and it delivers; a template otherwise. The wall's
    rules cap a post at 400 characters, so everything is trimmed to fit."""
    text = None
    try:
        text = _claude(b)
    except Exception:
        pass
    return (text or _template(b, random.Random(b["id"])))[:400]


def post(c, b, text):
    fs(c, "/messages", "POST", {"fields": {
        "n": {"stringValue": NAME}, "x": {"stringValue": text},
        "re": {"stringValue": b["drafter"]},
        "t": {"timestampValue": datetime.datetime.now(datetime.timezone.utc).isoformat()}}})


def main():
    c = config()
    if not c:
        print("docs/config.json not filled in — no wall to post to (see README)")
        return
    try:
        with open("docs/fixtures.json") as f:
            fx = json.load(f)
    except (OSError, ValueError):
        print("no fixtures.json — nothing to sledge")
        return
    found = beats(fx)
    try:
        with open(SEEN) as f:
            seen = json.load(f).get("done", [])
    except (OSError, ValueError):
        seen = None
    if seen is None:                     # first run: old defeats stay unsledged, like notify's marker
        json.dump({"done": [b["id"] for b in found]}, open(SEEN, "w"))
        print(f"first run — {len(found)} past defeat(s) recorded, none sledged")
        return
    fresh = [b for b in found if b["id"] not in seen]
    posted = 0
    for b in fresh[:PER_RUN]:
        text = sledge(b)
        try:
            post(c, b, text)
        except Exception as e:
            print(f"post failed for {b['drafter']}: {type(e).__name__}")
            continue
        seen.append(b["id"])
        posted += 1
        print(f"sledged {b['drafter']} ({b['their_team']} lost to undrafted {b['beaten_by']}): {text}")
    json.dump({"done": seen[-400:]}, open(SEEN, "w"))
    if not posted:
        print(f"no new defeats by undrafted teams ({len(found)} already sledged or seen)")


if __name__ == "__main__":
    main()
