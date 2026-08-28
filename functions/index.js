// Instant banter pushes: fires the moment a message document lands on the wall and
// web-pushes every subscribed phone (~2s door to door), then advances the same
// meta/notify marker the GitHub "UTC banter pings" workflow uses — so the workflow
// stays on as a safety net that only ever sends what this function missed.
//
// Deploy (one-off, from the repo root, needs the Blaze plan — see README):
//   npx firebase-tools login
//   npx firebase-tools functions:secrets:set VAPID_PRIVATE_KEY
//   npx firebase-tools deploy --only functions
"use strict";
const {onDocumentCreated} = require("firebase-functions/v2/firestore");
const {defineSecret} = require("firebase-functions/params");
const admin = require("firebase-admin");
const webpush = require("web-push");

// Keep these in step with docs/config.json (vapidPublicKey) and the site URL.
// If the VAPID pair is ever rotated: update here AND docs/config.json AND both
// secrets (GitHub Actions + firebase functions:secrets:set), then redeploy.
const VAPID_PUBLIC_KEY = "BAoJ_fc_noeOSlpQ0MJVKKBGWR2ls6dOaqLidUHx04nyfiMuzkL6lqhBzcQem3jd_zFCIcvrkRiGlU0cCBtM610";
const SITE = "https://wkesby.github.io/utc-2027/";
const VAPID_SUB = "mailto:utc-bot@users.noreply.github.com";

const VAPID_PRIVATE_KEY = defineSecret("VAPID_PRIVATE_KEY");

admin.initializeApp();

exports.pushOnMessage = onDocumentCreated({
  document: "messages/{id}",
  region: "australia-southeast1",   // must match the Firestore database's region
  secrets: [VAPID_PRIVATE_KEY],
  maxInstances: 2,                  // the wall is 11 mates; cap any runaway cost
  retry: false,
}, async (event) => {
  const snap = event.data;
  if (!snap) return;
  const m = snap.data();
  const db = admin.firestore();
  webpush.setVapidDetails(VAPID_SUB, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY.value());

  const title = m.re ? `💬 ${m.n} → ${m.re}` : `💬 ${m.n}`;
  const payload = JSON.stringify({
    title,
    body: String(m.x || "").slice(0, 180),
    url: SITE + "#banter",
    tag: "utc-banter",
  });

  const subs = await db.collection("subs").get();
  let sent = 0, dead = 0, skipped = 0;
  await Promise.all(subs.docs.map(async (d) => {
    if (m.n && d.get("n") === m.n) { skipped++; return; }  // your own sledge isn't news
    let sub;
    try { sub = JSON.parse(d.get("sub")); } catch (e) { return; }
    try {
      await webpush.sendNotification(sub, payload);
      sent++;
    } catch (e) {
      if (e.statusCode === 404 || e.statusCode === 410) {   // phone unsubscribed
        dead++;
        await d.ref.delete().catch(() => {});
      } else {
        console.warn("push failed:", e.statusCode || e.message);
      }
    }
  }));

  // Move the fallback marker forward (never backward, in case events arrive out of
  // order) so the workflow doesn't re-send this message.
  const marker = db.doc("meta/notify");
  await db.runTransaction(async (tx) => {
    const cur = (await tx.get(marker)).get("last");
    if (m.t && (!cur || !cur.toMillis || m.t.toMillis() > cur.toMillis())) {
      tx.set(marker, {last: m.t}, {merge: true});
    }
  }).catch((e) => console.warn("marker update failed:", e.message));

  console.log(`pushed "${title}" to ${sent} phone(s), ${dead} dead subscription(s) removed, ` +
      `${skipped} skipped (sender's own)`);
});
