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
- 04:00 AEST daily: standings refresh from live feeds.
- 25 past each hour: new banter-wall posts go out as phone notifications (once the section below is set up).
- 14:00 Melbourne Tuesday: report built, ladder image rendered, **pushed as a notification to every phone that opted in**, and emailed to you with a **one-tap WhatsApp share link** for anyone still on the old channel — tap, choose the group, send. WhatsApp has no official way for software to post into a group, so that tap stays human; notifications from the app itself don't need it.

## Switch on banter & notifications (10 minutes, once, free, optional)
The app's **Banter** tab is a wall where the group comments on each other's performance under their own names (plus a Sledge button on every drafter profile), and the app can send **proper phone notifications** — new banter and the Tuesday wrap land in the app instead of via WhatsApp. GitHub Pages can't store messages, so this one feature needs a free database:

1. [console.firebase.google.com](https://console.firebase.google.com) → **Add project** (any name, Google Analytics off). The free Spark plan is far more than 11 drafters will ever use; no card needed.
2. **Build → Firestore Database → Create database** → production mode → location `australia-southeast1`.
3. **Rules** tab → paste the contents of `firestore.rules` from this repo → **Publish**. (These rules are the security: size-capped posts, no edits or deletes.)
4. **Project settings (⚙) → General → Your apps → Web (`</>`)** → register an app (skip hosting) → copy its `projectId` and `apiKey` into `docs/config.json`. That key is a public identifier, not a secret — the rules do the guarding.
5. On your Mac: `pip install pywebpush && python -m utc.vapid` → the **public key** goes in `docs/config.json` (`vapidPublicKey`), the **private key** goes in **Settings → Secrets and variables → Actions** as `VAPID_PRIVATE_KEY`. Never commit the private key.
6. Commit `docs/config.json`. Done: the Banter tab lights up for everyone, and each drafter flicks notifications on inside the app. iPhone needs the app installed to the Home Screen (iOS 16.4+); Android works installed or in Chrome.

Posting names are an honour system, same as the tipping. If the wall ever needs moderating, delete documents in the Firebase console (the app can't).

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
