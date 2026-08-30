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
const cb = require("./comeback");

// Keep these in step with docs/config.json (vapidPublicKey) and the site URL.
// If the VAPID pair is ever rotated: update here AND docs/config.json AND both
// secrets (GitHub Actions + firebase functions:secrets:set), then redeploy.
const VAPID_PUBLIC_KEY = "BAoJ_fc_noeOSlpQ0MJVKKBGWR2ls6dOaqLidUHx04nyfiMuzkL6lqhBzcQem3jd_zFCIcvrkRiGlU0cCBtM610";
const SITE = "https://wkesby.github.io/utc-2027/";
const VAPID_SUB = "mailto:utc-bot@users.noreply.github.com";

const VAPID_PRIVATE_KEY = defineSecret("VAPID_PRIVATE_KEY");
const ANTHROPIC_API_KEY = defineSecret("ANTHROPIC_API_KEY");

admin.initializeApp();

exports.pushOnMessage = onDocumentCreated({
  document: "messages/{id}",
  region: "australia-southeast1",   // must match the Firestore database's region
  secrets: [VAPID_PRIVATE_KEY, ANTHROPIC_API_KEY],
  maxInstances: 2,                  // the wall is 11 mates; cap any runaway cost
  timeoutSeconds: 120,              // pushes finish in seconds; a comeback waits on Claude
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

  // The Commentator talks back: a drafter reply to one of its posts gets an instant,
  // escalating comeback. Writing it re-triggers this function, which pushes it like any
  // other post; the author check in talkBack stops any loop, and the workflow's comeback
  // step stays as the safety net — both sides skip replies that already have an answer.
  try {
    await talkBack(db, event.params.id, m);
  } catch (e) {
    console.warn("comeback failed:", e.message);
  }
});

async function talkBack(db, id, m) {
  if (m.n === cb.NAME || !m.p) return;
  const parent = await db.doc("messages/" + m.p).get();
  if (!parent.exists || parent.get("n") !== cb.NAME) return;
  const done = await db.collection("messages")
      .where("p", "==", id).where("n", "==", cb.NAME).limit(1).get();
  if (!done.empty) return;                         // the workflow got there first
  const chain = [];
  let cur = {id, n: m.n, x: m.x, p: m.p};
  const seen = new Set();
  while (cur && !seen.has(cur.id) && chain.length < 12) {
    seen.add(cur.id);
    chain.push(cur);
    if (!cur.p) break;
    const d = await db.doc("messages/" + cur.p).get();
    cur = d.exists ? {id: d.id, n: d.get("n"), x: d.get("x"), p: d.get("p") || ""} : null;
  }
  chain.reverse();
  const level = cb.escalation(chain);
  if (level > cb.MAX_LEVEL) return;                // The Commentator rests
  const text = await cb.generate({
    apiKey: ANTHROPIC_API_KEY.value(), thread: chain,
    msg: {id, n: m.n, x: m.x}, dossier: await dossierFor(m.n), level,
  });
  await db.collection("messages").add({
    n: cb.NAME, x: text, re: String(m.n).slice(0, 40), p: id,
    t: admin.firestore.Timestamp.now(),
  });
  console.log(`level ${level} comeback to ${m.n}`);
}

// Ammunition from the published site: where they sit, and their demerit record.
async function dossierFor(name) {
  const out = {};
  try {
    const S = await (await fetch(SITE + "standings.json")).json();
    for (const r of S.ladder || []) {
      if (r.drafter === name) {
        out.ladder_position = `${r.pos} of ${S.ladder.length}`;
        out.points = r.total;
      }
    }
  } catch (e) { /* sledge without it */ }
  try {
    const dm = await (await fetch(SITE + "demerits.json")).json();
    const n = (dm.losses || []).filter((l) => l.dr === name).length;
    if (n) out.demerits_for_losing_to_undrafted_teams = n;
  } catch (e) { /* sledge without it */ }
  return out;
}
