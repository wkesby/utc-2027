"""Monday update: text summary + PNG ladder, diffed against last week's standings."""
import json, os, datetime
from PIL import Image, ImageDraw, ImageFont
from .banter import commentary

def _font(size, bold=False):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def ladder_png(S, prev, path):
    W, rowh, top = 900, 54, 150
    H = top + rowh * len(S["ladder"]) + 60
    im = Image.new("RGB", (W, H), "#0B1220"); d = ImageDraw.Draw(im)
    d.text((40, 34), "UTC 2027", font=_font(46, True), fill="#FFC21A")
    d.text((40, 92), f"Standings · {datetime.date.today():%A %d %B %Y}", font=_font(22), fill="#8A94A8")
    prevpos = {r["drafter"]: r["pos"] for r in (prev or {}).get("ladder", [])}
    for i, r in enumerate(S["ladder"]):
        y = top + i * rowh
        d.rectangle([30, y, W - 30, y + rowh - 6], fill="#121A2B" if i % 2 else "#101726")
        d.text((50, y + 13), f"{r['pos']}", font=_font(26, True), fill="#FFC21A")
        d.text((100, y + 13), r["drafter"], font=_font(26, True), fill="#EEF2F7")
        mv = prevpos.get(r["drafter"])
        arrow = "" if not mv or mv == r["pos"] else (f"▲{mv - r['pos']}" if mv > r["pos"] else f"▼{r['pos'] - mv}")
        d.text((330, y + 16), arrow, font=_font(20, True), fill="#3DD98B" if arrow.startswith("▲") else "#FF5A4E")
        d.text((430, y + 16), f"confirmed {r['confirmed']}", font=_font(18), fill="#8A94A8")
        d.text((620, y + 16), f"in play {r['inplay']}", font=_font(18), fill="#8A94A8")
        d.text((W - 140, y + 10), f"{r['total']}", font=_font(30, True), fill="#EEF2F7")
    d.text((40, H - 42), f"{sum(1 for s in S['sports'].values() if not s['source'].startswith(('awaiting', 'feed error')))}/20 competitions scoring · in-play points move weekly; confirmed points are final", font=_font(16), fill="#8A94A8")
    im.save(path)

def share_page(S, site, stamp, path):
    """OG wrapper for the ladder PNG — WhatsApp only builds preview cards from HTML pages
    with Open Graph tags, never from a raw image URL. Unique URL per report dodges
    WhatsApp's per-URL preview cache."""
    base = site.rstrip("/")
    title = f"UTC 2027 — Monday update, {datetime.date.today():%d %b}"
    lead = S["ladder"][0]
    desc = f"{lead['drafter']} leads on {lead['total']} · tap for the full ladder"
    height = 150 + 54 * len(S["ladder"]) + 60
    open(path, "w").write(f"""<!doctype html><html><head><meta charset="utf-8">
<title>{title}</title>
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{base}/reports/{stamp}.html">
<meta property="og:image" content="{base}/reports/{stamp}.png">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="900">
<meta property="og:image:height" content="{height}">
<meta name="twitter:card" content="summary_large_image">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head><body style="margin:0;background:#0B1220;text-align:center">
<a href="{base}/"><img src="{stamp}.png" alt="{title}" style="max-width:100%"></a>
</body></html>""")

def summary(S, prev):
    prevtot = {r["drafter"]: r for r in (prev or {}).get("ladder", [])}
    lines = [f"*UTC 2027 — Monday update, {datetime.date.today():%d %b}*", ""]
    for r in S["ladder"]:
        p = prevtot.get(r["drafter"])
        delta = f" ({r['total'] - p['total']:+d})" if p else ""
        lines.append(f"{r['pos']}. {r['drafter']} — {r['total']}{delta}")
    movers = sorted(((r["total"] - prevtot[r["drafter"]]["total"], r["drafter"]) for r in S["ladder"] if r["drafter"] in prevtot), reverse=True)
    if movers and movers[0][0] > 0:
        lines += ["", f"Mover of the week: {movers[0][1]} (+{movers[0][0]})"]
    if movers and movers[-1][0] < 0:
        lines.append(f"Slider of the week: {movers[-1][1]} ({movers[-1][0]:+d})")
    quips = commentary(S, prev)
    if quips:
        lines += ["", "*From the commentary box:*"] + quips
    live = [s["name"] for s in S["sports"].values() if s["source"].startswith(("feed", "override", "confirmed"))]
    lines += ["", f"Scoring now: {', '.join(live) if live else 'nothing yet'}"]
    site = os.environ.get("SITE_URL", "")
    if site:
        # first URL in the message wins the WhatsApp preview — OG share page before the site link
        lines.append(f"Ladder: {site.rstrip('/')}/reports/{datetime.date.today().isoformat()}.html")
    lines.append("Full table: " + (site or "(site link)"))
    return "\n".join(lines)

if __name__ == "__main__":
    S = json.load(open("docs/standings.json"))
    prev = json.load(open("docs/last_week.json")) if os.path.exists("docs/last_week.json") else None
    os.makedirs("docs/reports", exist_ok=True)
    stamp = datetime.date.today().isoformat()
    ladder_png(S, prev, f"docs/reports/{stamp}.png")
    if os.environ.get("SITE_URL"):
        share_page(S, os.environ["SITE_URL"], stamp, f"docs/reports/{stamp}.html")
    text = summary(S, prev)
    open(f"docs/reports/{stamp}.txt", "w").write(text)
    json.dump(S, open("docs/last_week.json", "w"))
    print(text)
