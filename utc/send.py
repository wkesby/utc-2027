"""Email the Tuesday update (text + PNG) with a one-tap WhatsApp share link. Needs SMTP secrets in the workflow."""
import os, smtplib, ssl, datetime, urllib.parse, glob
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

def main():
    stamp = datetime.date.today().isoformat()
    text = open(f"docs/reports/{stamp}.txt").read()
    site = os.environ.get("SITE_URL", "").strip()
    user, password, to = env("SMTP_USER"), env("SMTP_PASS"), env("REPORT_TO")
    wa = "https://wa.me/?text=" + urllib.parse.quote(text)
    msg = EmailMessage()
    msg["Subject"] = f"UTC 2027 — Tuesday update {stamp}"
    msg["From"] = user; msg["To"] = to
    msg.set_content(f"{text}\n\nShare to WhatsApp (one tap, then pick the group):\n{wa}\n\nLadder image attached. Live table: {site}")
    with open(f"docs/reports/{stamp}.png", "rb") as f:
        msg.add_attachment(f.read(), maintype="image", subtype="png", filename=f"utc-{stamp}.png")
    with smtplib.SMTP_SSL(env("SMTP_HOST", "smtp.gmail.com"), 465, context=ssl.create_default_context()) as s:
        s.login(user, password); s.send_message(msg)
    print("sent to", to)

if __name__ == "__main__":
    main()
