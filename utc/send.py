"""Email the Monday update (text + PNG) with a one-tap WhatsApp share link. Needs SMTP secrets in the workflow."""
import os, smtplib, ssl, datetime, urllib.parse, glob
from email.message import EmailMessage

def main():
    stamp = datetime.date.today().isoformat()
    text = open(f"docs/reports/{stamp}.txt").read()
    site = os.environ.get("SITE_URL", "")
    wa = "https://wa.me/?text=" + urllib.parse.quote(text)
    msg = EmailMessage()
    msg["Subject"] = f"UTC 2027 — Monday update {stamp}"
    msg["From"] = os.environ["SMTP_USER"]; msg["To"] = os.environ["REPORT_TO"]
    msg.set_content(f"{text}\n\nShare to WhatsApp (one tap, then pick the group):\n{wa}\n\nLadder image attached. Live table: {site}")
    with open(f"docs/reports/{stamp}.png", "rb") as f:
        msg.add_attachment(f.read(), maintype="image", subtype="png", filename=f"utc-{stamp}.png")
    with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST", "smtp.gmail.com"), 465, context=ssl.create_default_context()) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"]); s.send_message(msg)
    print("sent to", os.environ["REPORT_TO"])

if __name__ == "__main__":
    main()
