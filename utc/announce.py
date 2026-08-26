"""One-off announcement email: the app is live, with iPhone/Android install steps and a
one-tap WhatsApp share link. Run from the 'UTC announcement' workflow, not on a schedule."""
import os, datetime, smtplib, ssl, urllib.parse
from email.message import EmailMessage
from .send import env, recipients

def message(site, path="data/announcement.txt"):
    """The announcement body lives in data/announcement.txt so a new one is an edit and a
    workflow run, not a code change. {SITE} is replaced with the live site URL."""
    base = site.rstrip("/")
    try:
        with open(path) as f:
            body = f.read().strip()
        if body:
            return body.replace("{SITE}", base)
    except OSError:
        pass
    return "\n".join([
        "*UTC 2027 — the ladder is now an app*",
        "",
        "Live standings, every drafter's stats and the full draft board, on your phone. "
        "Updates itself daily, works offline, no login.",
        "",
        f"Get it: {base}/app.html",
        "",
        "iPhone: open that link in Safari, tap Share, then Add to Home Screen.",
        "Android: open it in Chrome, tap the three dots, then Install app.",
        "",
        "Inside: the ladder with overnight movers, steal and bust of the season, points above par, "
        "all 20 competitions with the draft board, and a head-to-head record against every other drafter.",
        "",
        "No account, no app store. If your picks are going badly, that is not a bug.",
    ])

def main():
    site = os.environ.get("SITE_URL", "https://wkesby.github.io/utc-2027/").strip()
    user, password, to = env("SMTP_USER"), env("SMTP_PASS"), recipients(env("REPORT_TO"))
    text = message(site)
    wa = "https://wa.me/?text=" + urllib.parse.quote(text)
    msg = EmailMessage()
    msg["Subject"] = f"UTC 2027 — app update {datetime.date.today():%d %b} (share this with the group)"
    msg["From"] = user; msg["To"] = ", ".join(to)
    msg.set_content(
        f"{text}\n\n"
        f"— — —\nShare to WhatsApp (one tap, then pick the group):\n{wa}\n\n"
        f"The link in the message opens an install page with the iPhone and Android steps, "
        f"so nobody has to ask you how to do it.\n")
    with smtplib.SMTP_SSL(env("SMTP_HOST", "smtp.gmail.com"), 465, context=ssl.create_default_context()) as s:
        s.login(user, password); s.send_message(msg)
    print(f"announcement sent to {len(to)} recipient(s):", ", ".join(to))

if __name__ == "__main__":
    main()
