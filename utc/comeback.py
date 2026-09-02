"""Talk back to The Commentator and The Commentator talks back harder. Runs from the
5-minute banter workflow: any drafter reply aimed at a Commentator post gets a comeback,
written by Claude with the whole thread and a dossier on the replier (ladder spot, points,
demerits) — and each round of the same thread steps the sledging up a level. The comeback
itself is the dedup marker (a reply that already has one is never answered again), the
heat caps at level 5 per thread before The Commentator rests, and — like the rest of the
chain — no Claude, no key, or any error falls back to canned lines and never breaks the
workflow.

    python -m utc.comeback
"""
import datetime, json, os, random, urllib.request
from .notify import config, fs
from .trashtalk import NAME

MAX_LEVEL = 5        # comebacks per thread; after that The Commentator has said his piece
PER_RUN = 3
FRESH_HOURS = 24     # never dredge up stale replies (matters most on the first run)


def ts(s):
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch(c, limit=100):
    q = fs(c, ":runQuery", "POST", {"structuredQuery": {"from": [{"collectionId": "messages"}],
         "orderBy": [{"field": {"fieldPath": "t"}, "direction": "DESCENDING"}], "limit": limit}})
    out = []
    for d in [x["document"] for x in q if "document" in x]:
        f = d["fields"]
        g = lambda k: (f.get(k) or {}).get("stringValue") or (f.get(k) or {}).get("timestampValue") or ""
        out.append({"id": d["name"].split("/")[-1], "n": g("n"), "x": g("x"),
                    "re": g("re"), "p": g("p"), "t": g("t")})
    return out


def pending(msgs, now=None):
    """Fresh human replies to a Commentator post that don't have a comeback yet, each with
    its thread (oldest first) and the escalation level for the response."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(hours=FRESH_HOURS)
    by_id = {m["id"]: m for m in msgs}
    answered = {m["p"] for m in msgs if m["n"] == NAME and m["p"]}
    out = []
    for m in msgs:
        if m["n"] == NAME or not m["p"] or m["id"] in answered:
            continue
        parent = by_id.get(m["p"])
        if not parent or parent["n"] != NAME:
            continue
        when = ts(m["t"])
        if not when or when < cutoff:
            continue
        chain, cur, seen = [], m, set()
        while cur and cur["id"] not in seen and len(chain) < 12:
            seen.add(cur["id"])
            chain.append(cur)
            cur = by_id.get(cur["p"]) if cur["p"] else None
        level = sum(1 for c in chain if c["n"] == NAME)
        if level > MAX_LEVEL:                    # The Commentator rests
            continue
        out.append({"msg": m, "level": level, "thread": list(reversed(chain))})
    return sorted(out, key=lambda x: x["msg"]["t"])[:PER_RUN]


def dossier(name):
    """Ammunition: where they sit, what they're on, and their demerit record."""
    out = {}
    try:
        S = json.load(open("docs/standings.json"))
        for r in S["ladder"]:
            if r["drafter"] == name:
                out["ladder_position"] = f"{r['pos']} of {len(S['ladder'])}"
                out["points"] = r["total"]
    except (OSError, ValueError, KeyError):
        pass
    try:
        dm = json.load(open("docs/demerits.json"))
        n = sum(1 for l in dm.get("losses", []) if l["dr"] == name)
        if n:
            out["demerits_for_losing_to_undrafted_teams"] = n
    except (OSError, ValueError, KeyError):
        pass
    return out


def _claude(item):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    m, level = item["msg"], item["level"]
    body = {"model": "claude-opus-5", "max_tokens": 300,
            "system": ("You are The Commentator, the resident AI sledger on the banter wall of an "
                       "11-mate Australian sports tipping comp (the UTC) — a private wall where "
                       "these blokes abuse each other for sport and have asked you to give it back "
                       "harder. A drafter has replied to one of your posts, talking back. Write "
                       "your comeback: one line, plain text, under 60 words, broad Aussie pub "
                       "banter, first names only, no emojis, no hashtags, no quotes, no preamble. "
                       "Swear, and swear properly: this is a wall where 'fuck you Commentator' is "
                       "a normal Tuesday, so profanity belongs in most lines — fuck, shit, "
                       "bastard, wanker, dickhead, the full Australian vocabulary — dropped in the "
                       "natural way mates use it, not sprinkled on as decoration. Never soften or "
                       "sanitise a line to be polite; if it reads like a broadcaster, rewrite it "
                       "as a bloke at the pub. Be specific and "
                       "personal about their comp record: name their teams, their picks, their "
                       "ladder position, their points, their demerits, and hold them to it. Use "
                       "only facts from the thread and the dossier; never invent results. Keep it "
                       "to the tipping — their picks, their results, their standing in this comp — "
                       "and leave family, looks, health and anything a mate could not laugh off "
                       f"out of it. This is escalation level {level} of {MAX_LEVEL}: level 1 is a "
                       "dismissive backhander, and every level after goes harder, ruder and more "
                       f"personal about how badly they are going. At level {MAX_LEVEL} deliver the "
                       "knockout — the most brutal line their record justifies — and make clear "
                       "The Commentator rests."),
            "messages": [{"role": "user", "content": json.dumps({
                "thread": [{"who": c["n"], "said": c["x"]} for c in item["thread"]],
                "replying_to": {"who": m["n"], "said": m["x"]},
                "dossier_on_them": dossier(m["n"]),
                "escalation_level": level})}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        msg = json.load(r)
    if msg.get("stop_reason") == "refusal":
        return None
    text = " ".join("".join(b.get("text", "") for b in msg.get("content", [])
                            if b.get("type") == "text").split())
    return text or None


TEMPLATES = {
    1: ["Cute, {who}. I've seen your picks — you don't get to have fucking opinions.",
        "Noted, {who}. Take it up with the scoreboard, mate, it wrote the bloody material."],
    2: ["{who}, you're abusing software while your teams do the actual embarrassing. Christ.",
        "Big words, {who}, from a bloke whose draft board is a fucking crime scene."],
    3: ["Mate, {who}, you've got a shithouse ladder position to explain before you start on me.",
        "{who}, every reply drags your record further into it. Keep fucking going, I've got all season."],
    4: ["{who}, I've got receipts and you've got excuses. Piss off and check on your teams — they need you more than this thread does.",
        "Shocking matchup this, {who}. I'm a scoreboard with a mouth and you're the poor bastard it keeps humiliating."],
    5: ["That's the bell, {who}. Your points are shit, your demerits are on the board, and you just lost an argument to software. The Commentator rests.",
        "Final word, {who}: I don't fucking miss and you don't win. Go have a lie down with that draft board. The Commentator rests."],
}


def comeback(item):
    text = None
    try:
        text = _claude(item)
    except Exception:
        pass
    if not text:
        m, level = item["msg"], item["level"]
        text = random.Random(m["id"]).choice(TEMPLATES[min(level, MAX_LEVEL)]).format(who=m["n"])
    return text[:400]


def post(c, item, text):
    m = item["msg"]
    fs(c, "/messages", "POST", {"fields": {
        "n": {"stringValue": NAME}, "x": {"stringValue": text},
        "re": {"stringValue": m["n"][:40]}, "p": {"stringValue": m["id"]},
        "t": {"timestampValue": datetime.datetime.now(datetime.timezone.utc).isoformat()}}})


def main():
    c = config()
    if not c:
        print("docs/config.json not filled in — no wall (see README)")
        return
    todo = pending(fetch(c))
    if not todo:
        print("no unanswered replies to The Commentator")
        return
    for item in todo:
        text = comeback(item)
        try:
            post(c, item, text)
        except Exception as e:
            print(f"comeback to {item['msg']['n']} failed: {type(e).__name__}")
            continue
        print(f"level {item['level']} comeback to {item['msg']['n']}: {text}")


if __name__ == "__main__":
    main()
