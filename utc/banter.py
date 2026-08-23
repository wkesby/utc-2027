"""Commentary for the Monday email: friendly banter and light sledging built from the week's
ladder. Uses the Claude API (claude-opus-5) when ANTHROPIC_API_KEY is set — fresh lines every
week; otherwise falls back to date-seeded templates. Never allowed to break the report."""
import json, os, random, urllib.request

def _facts(S, prev):
    prevtot = {r["drafter"]: r["total"] for r in (prev or {}).get("ladder", [])}
    prevpos = {r["drafter"]: r["pos"] for r in (prev or {}).get("ladder", [])}
    lad = [{"pos": r["pos"], "drafter": r["drafter"], "total": r["total"],
            "delta": r["total"] - prevtot[r["drafter"]] if r["drafter"] in prevtot else None,
            "moved": prevpos[r["drafter"]] - r["pos"] if r["drafter"] in prevpos else None}
           for r in S["ladder"]]
    live, unranked = [], []
    for s in S["sports"].values():
        if not s["source"].startswith(("feed", "override", "confirmed")):
            continue
        ranked = [r for r in s["rows"] if r["rank"] is not None]
        live.append({"comp": s["name"],
                     "leader": {"drafter": ranked[0]["drafter"], "pick": ranked[0]["pick"]} if ranked else None,
                     "last": {"drafter": ranked[-1]["drafter"], "pick": ranked[-1]["pick"]} if ranked else None})
        unranked += [{"drafter": r["drafter"], "pick": r["pick"], "comp": s["name"]}
                     for r in s["rows"] if r["rank"] is None]
    return {"ladder": lad, "live_comps": live, "picks_not_in_their_comp": unranked}

def _claude(facts):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = {"model": "claude-opus-5", "max_tokens": 1000,
            "system": ("You write the commentary for a weekly email to an 11-mate Australian sports "
                       "tipping comp (the UTC: each drafter picked one team per competition, points for "
                       "where their pick finishes). Reply with 2-3 short lines of friendly banter and "
                       "light sledging about this week's ladder — first names, PG, Aussie tone, plain "
                       "text, one sledge per line, no emojis or hashtags, no preamble. Use only the "
                       "facts given; never invent results."),
            "messages": [{"role": "user", "content": json.dumps(facts)}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        msg = json.load(r)
    if msg.get("stop_reason") == "refusal":
        return None
    text = "".join(b.get("text", "") for b in msg.get("content", []) if b.get("type") == "text")
    return [l.strip() for l in text.splitlines() if l.strip()][:4] or None

def _templates(facts, rng):
    lad = facts["ladder"]
    top, bottom = lad[0], lad[-1]
    lines = [rng.choice([
        f"{top['drafter']} on top of the pile — savour it, the season is about 5% done.",
        f"{top['drafter']} leads. Somewhere a group chat is already calling it a fluke.",
        f"Early crown for {top['drafter']}. History is not kind to August leaders.",
        f"{top['drafter']} first on the ladder and unbearable already."])]
    if facts["picks_not_in_their_comp"] and rng.random() < 0.7:
        u = rng.choice(facts["picks_not_in_their_comp"])
        lines.append(rng.choice([
            f"{u['drafter']} drafted {u['pick']} in the {u['comp']} — a competition {u['pick']} didn't qualify for. Bold.",
            f"Reminder that {u['drafter']}'s {u['comp']} pick, {u['pick']}, is not actually in the {u['comp']}."]))
    lines.append(rng.choice([
        f"{bottom['drafter']} props up the table on {bottom['total']}. Someone has to hold the ladder steady.",
        f"Wooden spoon watch: {bottom['drafter']}. It's a marathon, mate, but you're jogging backwards.",
        f"{bottom['drafter']} is last. The draft board remembers who laughed on draft night.",
        f"Spare a thought for {bottom['drafter']} on {bottom['total']}. Or don't."]))
    if len(lad) > 1 and lad[0]["total"] - lad[1]["total"] <= 2 and rng.random() < 0.5:
        lines.append(f"{lad[1]['drafter']} is {lad[0]['total'] - lad[1]['total']} back — nothing one bad weekend can't fix.")
    return lines

def commentary(S, prev):
    facts = _facts(S, prev)
    try:
        lines = _claude(facts)
        if lines:
            return lines
    except Exception:
        pass
    return _templates(facts, random.Random(S["generated"][:10]))
