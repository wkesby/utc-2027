# UTC 2027 — live standings

Scores the Ultimate Tipping Comp automatically: feeds → competition order → UTC points (11 down to 1, +2 for a win), split into **in play** and **confirmed**. Publishes an installable phone app (ladder, per-drafter stats, competition browser, banter wall) and a weekly report.

## Setup (15 minutes, once)
1. Create a **public** GitHub repository called `utc-2027` and upload everything in this folder (or push it with git / Claude Code).
2. **Settings → Pages → Source: Deploy from a branch → main / docs**. Your link is `https://<username>.github.io/utc-2027/` — share that with the group.
3. **Settings → Secrets and variables → Actions**:
   - Variables: `SITE_URL` = the link above.
   - Secrets (for the weekly email): `SMTP_USER` (a Gmail address), `SMTP_PASS` (a Gmail *app password*, not your login), `REPORT_TO` (where the update goes — you).
4. **Actions → UTC standings → Run workflow** once to prove it. The first run creates `docs/standings.json`, a report and the ladder PNG.

## How the week works
- Hourly: standings, fixtures and results refresh from the live feeds, so the ladder follows the games through the day. (The app also overlays live in-game scores itself while you watch the Fixtures tab.)
- Every 5 minutes: new banter-wall posts go out as phone notifications (once the section below is set up) — GitHub's scheduler adds a little jitter, so a sledge typically lands within a few minutes, or in ~2 seconds with the instant upgrade below.
- 14:00 Melbourne Tuesday: report built, ladder image rendered, **pushed as a notification to every phone that opted in**, and emailed to you with a **one-tap WhatsApp share link** for anyone still on the old channel — tap, choose the group, send. WhatsApp has no official way for software to post into a group, so that tap stays human; notifications from the app itself don't need it.

## Switch on banter & notifications (10 minutes, once, free, optional)
The app's **Banter** tab is a wall where the group comments on each other's performance under their own names (plus a Sledge button on every drafter profile), and the app can send **proper phone notifications** — new banter and the Tuesday wrap land in the app instead of via WhatsApp. GitHub Pages can't store messages, so this one feature needs a free database:

1. [console.firebase.google.com](https://console.firebase.google.com) → **Add project** (any name, Google Analytics off). The free Spark plan is far more than 11 drafters will ever use; no card needed.
2. **Build → Firestore Database → Create database** → production mode → location `australia-southeast1`.
3. **Rules** tab → paste the contents of `firestore.rules` from this repo → **Publish**. (These rules are the security: size-capped posts, no edits or deletes.)
4. **Project settings (⚙) → General → Your apps → Web (`</>`)** → register an app (skip hosting) → copy its `projectId` and `apiKey` into `docs/config.json` — the pencil icon on github.com edits it right in the browser. That key is a public identifier, not a secret; the rules do the guarding. (`vapidPublicKey` is already filled in.)
5. **Settings → Secrets and variables → Actions → New repository secret**: name `VAPID_PRIVATE_KEY`, value = the private key that pairs with the committed public one (handed to the commissioner when this was set up). To use your own pair instead: `pip install pywebpush && python -m utc.vapid`, then update the secret **and** `vapidPublicKey` together — whoever holds the private key can notify every subscribed phone, so re-run that any time you want to rotate it.
6. **Actions → UTC banter check → Run workflow.** Every line prints PASS or FAIL with the fix. All PASS = the Banter tab is live and each drafter flicks notifications on inside the app — iPhone needs the app installed to the Home Screen (iOS 16.4+); Android works installed or in Chrome. Run it again with the *test notification* box ticked once your phone has opted in, and it should buzz.

Posting names are an honour system, same as the tipping. If the wall ever needs moderating, delete documents in the Firebase console (the app can't).

### Instant sledging (optional upgrade)
Out of the box a GitHub workflow pushes new banter every 5 minutes. For ~2-second delivery, deploy the included Cloud Function (`functions/`): it fires the moment a message lands and pushes immediately, and it advances the same marker the workflow uses — so the workflow becomes a safety net that only sends what the function missed, and nothing is ever sent twice.

1. Firebase console → ⚙ → **Usage and billing** → upgrade to the **Blaze** plan. A card is required, but this function sits comfortably inside the free quota (and `maxInstances` in `functions/index.js` caps any runaway), so the bill stays $0.
2. On your Mac, from the repo folder (needs Node.js — `brew install node` if you don't have it):
   ```
   npx firebase-tools login
   npx firebase-tools functions:secrets:set VAPID_PRIVATE_KEY   # paste the same key as the GitHub secret
   npx firebase-tools deploy --only functions
   ```
   The first deploy switches on several Google Cloud APIs and can take a few minutes.
3. Post on the wall from one phone with another phone opted in — the buzz should arrive within a couple of seconds.

If the deploy complains about the trigger location, the database isn't in `australia-southeast1`: change `region` in `functions/index.js` to the location shown at the top of the Firestore Data page and deploy again. Once instant delivery is confirmed, relax the schedule in `.github/workflows/banter.yml` from every 5 minutes to hourly — that's its safety-net cadence.

## Feeds
| Automatic (ESPN / Squiggle) | Manual for now (edit `data/overrides.json`) |
|---|---|
| NFL, EPL, Bundesliga, Champions League, NBA, NHL, MLB, NCAA, F1, NASCAR, AFL | NRL, cycling, MotoGP, V8 Supercars, ATP Race, women's tennis, golf, WSL, Champions Cup |

The ESPN adapter was written without live network access — the first Actions run is its first real test. If a feed misbehaves the page says so and shows nothing for that sport rather than rubbish; add the positions by hand in `overrides.json` and it takes precedence.

## The commissioner's file: `data/overrides.json`
- `positions`: `{"nrl": {"Penrith Panthers": 1, ...}}` — current order for sports with no feed (or a broken one).
- `confirmed`: `{"ncaa": {"Ohio State": 1, ...}}` — **final** order once a competition is over, applying the comp's own tie-breaks. Locks the points.
- `bonus`: `{"nfl": ["LA Rams"], "golf": ["Scottie Scheffler", "Rory McIlroy"]}` — winners; one entry per competition, major or slam won.
Trades: edit `data/picks.json` after each window.

## Files
`utc/sports.py` the 20 competitions · `utc/scoring.py` the points rules · `utc/engine.py` builds `docs/standings.json` · `utc/report.py` weekly text + PNG · `utc/send.py` email · `utc/notify.py` push notifications · `utc/vapid.py` one-off push keygen · `firestore.rules` banter-wall security · `feeds/` adapters · `docs/index.html` the phone app (installable PWA: Share → Add to Home Screen) · `docs/config.json` banter/notification config.
