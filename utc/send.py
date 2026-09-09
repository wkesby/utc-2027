"""Email the Tuesday update (text + PNG) with a one-tap WhatsApp share link. Needs SMTP secrets in the workflow."""
import os, re, html, smtplib, ssl, datetime, urllib.parse
from email.message import EmailMessage

def env(name, default=None):
    """Secrets pasted into GitHub often carry a trailing newline; a stray \\n or \\r in a
    header value makes EmailMessage raise, and in a password it breaks the SMTP login."""
    v = os.environ.get(name, default)
    if v is None:
        raise SystemExit(f"{name} is not set — add it under Settings > Secrets and variables > Actions")
    v = v.strip()
    if not v:
        raise SystemExit(f"{name} is empty")
    return v

def recipients(raw):
    """REPORT_TO may hold several addresses, one per line or comma/semicolon separated.
    A header value can't contain a newline, so they're joined with commas."""
    return [a.strip() for a in re.split(r"[\n\r,;]+", raw) if a.strip()]

WA_BUDGET = 2000   # characters of wa.me URL that iOS will still hand to WhatsApp

def wa_url(text):
    return "https://wa.me/?text=" + urllib.parse.quote(text)

def _drop(lines, head):
    """Remove the section opened by `head` up to the next *heading* or the 'Scoring now:'
    foot; the blank line that preceded the section now separates what's left."""
    if head not in lines:
        return lines
    a = lines.index(head)
    b = next((i for i in range(a + 1, len(lines))
              if lines[i].startswith("*") or lines[i].startswith("Scoring now:")), len(lines))
    return lines[:a] + lines[b:]

def share_text(text, budget=WA_BUDGET):
    """The WhatsApp-sized wrap. wa.me carries the message inside the URL, and iOS refuses
    to open one past a couple of thousand characters ('Link couldn't be opened') — the
    full wrap with every drafter's next games runs to 7,000. So the look-ahead goes first,
    then the commentary, then the scoring line; the ladder with the share link is the
    floor, and the link's preview shows the ladder image anyway. The email and the app
    always carry the lot."""
    lines = text.split("\n")
    trims = [lambda l: _drop(l, "*Next 7 days*"),
             lambda l: _drop(l, "*From the commentary box:*"),
             lambda l: [x for x in l if not x.startswith("Scoring now:")]]
    out = "\n".join(lines)
    for t in trims:
        if len(wa_url(out)) <= budget:
            break
        lines = t(lines)
        out = "\n".join(lines).strip()
    return out

def main():
    stamp = datetime.date.today().isoformat()
    text = open(f"docs/reports/{stamp}.txt").read()
    site = os.environ.get("SITE_URL", "").strip()
    user, password = env("SMTP_USER"), env("SMTP_PASS")
    to = recipients(env("REPORT_TO"))
    short = share_text(text)
    wa = wa_url(short)
    print(f"WhatsApp link: {len(wa)} chars" + (" (full wrap)" if short == text else f" (trimmed from {len(wa_url(text))})"))
    msg = EmailMessage()
    msg["Subject"] = f"UTC 2027 — Tuesday update {stamp}"
    msg["From"] = user; msg["To"] = ", ".join(to)
    msg.set_content(f"{text}\n\nShare to WhatsApp (one tap, then pick the group):\n{wa}\n\nLadder image attached. Live table: {site}")
    # Mail clients wrap and break a bare 2,000-character URL in plain text; the HTML
    # part carries it as a proper link, which is what a phone actually taps.
    font = "font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif"
    msg.add_alternative(
        f"<pre style='{font};font-size:15px;line-height:1.4;white-space:pre-wrap'>{html.escape(text)}</pre>"
        f"<p style='{font};font-size:16px'><a href='{html.escape(wa, quote=True)}'><b>Share to WhatsApp</b></a>"
        " — one tap, then pick the group.</p>"
        + (f"<p style='{font};font-size:14px'>Ladder image attached. Live table: "
           f"<a href='{html.escape(site, quote=True)}'>{html.escape(site)}</a></p>" if site else ""),
        subtype="html")
    with open(f"docs/reports/{stamp}.png", "rb") as f:
        msg.add_attachment(f.read(), maintype="image", subtype="png", filename=f"utc-{stamp}.png")
    with smtplib.SMTP_SSL(env("SMTP_HOST", "smtp.gmail.com"), 465, context=ssl.create_default_context()) as s:
        s.login(user, password); s.send_message(msg)
    print(f"sent to {len(to)} recipient(s):", ", ".join(to))

if __name__ == "__main__":
    main()
