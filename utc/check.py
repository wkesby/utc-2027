"""Banter setup checker — run from the 'UTC banter check' workflow (Actions tab) after
doing the README steps. Every line is PASS or FAIL with the fix, so a broken setup
never has to be debugged over WhatsApp."""
import base64, datetime, json, os, sys, urllib.error

from .notify import CONFIG, fs

results = []


def report(okay, what, fix=""):
    print(("PASS  " if okay else "FAIL  ") + what
          + ("" if okay or not fix else f"\n      fix: {fix}"))
    results.append(okay)


def finish():
    bad = results.count(False)
    print("\n" + ("ALL GOOD — banter and notifications are live. Run this again with "
                  "'test notification' ticked once you've turned them on, on your phone."
                  if not bad else f"{bad} problem(s) above — fix and run this again."))
    sys.exit(1 if bad else 0)


def main():
    try:
        with open(CONFIG) as f:
            cfg = json.load(f)
    except (OSError, ValueError) as e:
        report(False, "docs/config.json parses", str(e))
        finish()
    fb = cfg.get("firebase") or {}
    report(bool(fb.get("projectId")), "firebase.projectId filled in",
           "Firebase console → Project settings (⚙) → copy the Project ID into docs/config.json")
    report(bool(fb.get("apiKey")), "firebase.apiKey filled in",
           "Project settings → General → your web app's apiKey into docs/config.json")
    pub = cfg.get("vapidPublicKey", "")
    report(bool(pub), "vapidPublicKey filled in", "run: python -m utc.vapid")
    if not (fb.get("projectId") and fb.get("apiKey")):
        finish()

    c = {"firebase": fb}
    try:
        fs(c, ":runQuery", "POST",
           {"structuredQuery": {"from": [{"collectionId": "messages"}], "limit": 1}})
        report(True, "Firestore database reachable and readable")
    except urllib.error.HTTPError as e:
        report(False, f"Firestore database reachable and readable (HTTP {e.code})",
               "403: paste firestore.rules into Firestore → Rules and Publish. "
               "404: Build → Firestore Database → Create database, and check the projectId. "
               "400: apiKey doesn't belong to this project")
        finish()
    except Exception as e:
        report(False, "Firestore database reachable", str(e))
        finish()

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        fs(c, "/meta/setup", "PATCH", {"fields": {"checked": {"timestampValue": now}}})
        report(True, "Firestore writable")
    except Exception:
        report(False, "Firestore writable",
               "paste firestore.rules into Firestore → Rules and Publish")

    # The pasted rules must be the real ones, not console test mode: a junk post has to bounce.
    try:
        doc = fs(c, "/messages", "POST", {"fields": {"junk": {"stringValue": "probe"}}})
        try:
            fs(c, doc["name"], "DELETE")           # only possible if rules are wide open
        except Exception:
            pass
        report(False, "rules reject a malformed post",
               "the database accepted junk — paste firestore.rules into Firestore → Rules "
               "and Publish (test-mode rules leave the wall wide open)")
    except urllib.error.HTTPError:
        report(True, "rules reject a malformed post")

    priv = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    report(bool(priv), "VAPID_PRIVATE_KEY secret set",
           "repo Settings → Secrets and variables → Actions → New repository secret")
    if priv and pub:
        try:
            from cryptography.hazmat.primitives import serialization
            from py_vapid import Vapid
            derived = base64.urlsafe_b64encode(
                Vapid.from_string(priv).private_key.public_key().public_bytes(
                    serialization.Encoding.X962,
                    serialization.PublicFormat.UncompressedPoint)).rstrip(b"=").decode()
            report(derived == pub, "private key matches the app's vapidPublicKey",
                   "they're from different pairs — python -m utc.vapid makes a fresh pair; "
                   "update the secret AND docs/config.json together")
        except Exception as e:
            report(False, "VAPID private key parses", f"{e} — regenerate with python -m utc.vapid")
    finish()


if __name__ == "__main__":
    main()
