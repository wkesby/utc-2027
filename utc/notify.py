"""Push notifications to the installed app, replacing the WhatsApp relay for anyone
who flicks them on in the Banter tab. Two modes:

    python -m utc.notify banter   5-minute workflow: push banter-wall messages posted
                                  since the last run (marker kept in Firestore)
    python -m utc.notify report   Tuesday slot: push the weekly wrap headline

Plain Web Push (VAPID) sent with pywebpush; subscriptions live in the same Firestore
project as the banter wall, so there is no push server to run. Does nothing — and says
so — until docs/config.json is filled in and the VAPID_PRIVATE_KEY secret exists, and
never breaks the workflow that calls it."""
import datetime, json, os, sys, urllib.error, urllib.request

CONFIG = "docs/config.json"
FS = "https://firestore.googleapis.com/v1"


def config():
    try:
        with open(CONFIG) as f:
            c = json.load(f)
    except (OSError, ValueError):
        return None
    fb = c.get("firebase") or {}
    if not fb.get("projectId") or not fb.get("apiKey"):
        return None
    return c


def fs(c, path, method="GET", body=None):
    """One Firestore REST call. path is either '/collection[/doc]' under the default
    database, ':runQuery', or a full 'projects/...' resource name (for deletes)."""
    fb = c["firebase"]
    base = path if path.startswith("projects/") else \
        f"projects/{fb['projectId']}/databases/(default)/documents{path}"
    req = urllib.request.Request(
        f"{FS}/{base}?key={fb['apiKey']}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def val(fields, key):
    v = fields.get(key) or {}
    return v.get("stringValue") or v.get("timestampValue") or ""


def rows(query_result):
    return [d["document"] for d in query_result if "document" in d]


def subscriptions(c):
    out = []
    q = fs(c, ":runQuery", "POST",
           {"structuredQuery": {"from": [{"collectionId": "subs"}], "limit": 300}})
    for d in rows(q):
        try:
            out.append({"name": d["name"], "sub": json.loads(val(d["fields"], "sub"))})
        except (ValueError, KeyError):
            pass
    return out


def push_all(c, payload):
    priv = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    if not priv:
        print("VAPID_PRIVATE_KEY secret not set — nothing pushed (see README)")
        return
    targets = subscriptions(c)
    if not targets:
        print("nobody has switched notifications on yet")
        return
    from pywebpush import webpush, WebPushException
    claims_sub = os.environ.get("VAPID_SUB", "").strip() or "mailto:utc-bot@users.noreply.github.com"
    data = json.dumps(payload)
    sent = dead = failed = 0
    for t in targets:
        try:
            webpush(t["sub"], data, vapid_private_key=priv, vapid_claims={"sub": claims_sub})
            sent += 1
        except WebPushException as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (404, 410):          # phone unsubscribed or app removed
                try:
                    fs(c, t["name"], "DELETE")
                    dead += 1
                except Exception:
                    pass
            else:
                failed += 1
                print("push failed:", code or e)
    print(f"push: {sent} sent, {dead} dead subscriptions removed, {failed} failed")


def site_url():
    return os.environ.get("SITE_URL", "https://wkesby.github.io/utc-2027/").strip().rstrip("/") + "/"


def banter(c):
    """Push whatever landed on the wall since the marker; then move the marker."""
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    try:
        last = val(fs(c, "/meta/notify").get("fields", {}), "last")
    except urllib.error.HTTPError:
        last = ""                            # marker doc doesn't exist yet
    if not last:
        fs(c, "/meta/notify", "PATCH", {"fields": {"last": {"timestampValue": now}}})
        print("first run — marker set, history stays unpushed")
        return
    q = fs(c, ":runQuery", "POST", {"structuredQuery": {
        "from": [{"collectionId": "messages"}],
        "where": {"fieldFilter": {"field": {"fieldPath": "t"}, "op": "GREATER_THAN",
                                  "value": {"timestampValue": last}}},
        "orderBy": [{"field": {"fieldPath": "t"}, "direction": "ASCENDING"}],
        "limit": 50}})
    msgs = [{"n": val(d["fields"], "n"), "x": val(d["fields"], "x"),
             "re": val(d["fields"], "re")} for d in rows(q)]
    fs(c, "/meta/notify", "PATCH", {"fields": {"last": {"timestampValue": now}}})
    if not msgs:
        print("no new banter")
        return
    m = msgs[-1]
    aimed = f" → {m['re']}" if m["re"] else ""
    if len(msgs) == 1:
        title, body = f"💬 {m['n']}{aimed}", m["x"]
    else:
        title = "💬 UTC banter"
        body = f"{len(msgs)} new messages. Latest — {m['n']}{aimed}: {m['x']}"
    push_all(c, {"title": title, "body": body[:180],
                 "url": site_url() + "#banter", "tag": "utc-banter"})


def report(c):
    """The Tuesday wrap, straight to phones — same slot as the email."""
    with open("docs/standings.json") as f:
        lad = json.load(f)["ladder"]
    top = lad[0]
    body = f"{top['drafter']} leads on {top['total']}"
    if len(lad) > 1:
        body += f", {top['total'] - lad[1]['total']} clear of {lad[1]['drafter']}"
    body += ". Tap for the ladder, the movers and this week's sledging."
    push_all(c, {"title": "🏆 UTC 2027 — weekly wrap", "body": body,
                 "url": site_url() + "#ladder", "tag": "utc-report"})


def test(c):
    """From the 'UTC banter check' workflow: prove the whole push chain end to end."""
    push_all(c, {"title": "✅ UTC 2027", "body": "Notifications are working. "
                 "This is what a sledge will feel like.",
                 "url": site_url() + "#banter", "tag": "utc-test"})


def main():
    c = config()
    if not c:
        print("docs/config.json not filled in — notifications are off (see README)")
        return
    mode = sys.argv[1] if len(sys.argv) > 1 else "banter"
    {"report": report, "test": test}.get(mode, banter)(c)


if __name__ == "__main__":
    main()
