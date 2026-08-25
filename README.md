# UTC 2027 — live standings

Scores the Ultimate Tipping Comp automatically: feeds → competition order → UTC points (11 down to 1, +2 for a win), split into **in play** and **confirmed**. Publishes a phone-friendly page and a weekly report.

## Setup (15 minutes, once)
1. Create a **public** GitHub repository called `utc-2027` and upload everything in this folder (or push it with git / Claude Code).
2. **Settings → Pages → Source: Deploy from a branch → main / docs**. Your link is `https://<username>.github.io/utc-2027/` — share that with the group.
3. **Settings → Secrets and variables → Actions**:
   - Variables: `SITE_URL` = the link above.
   - Secrets (for the weekly email): `SMTP_USER` (a Gmail address), `SMTP_PASS` (a Gmail *app password*, not your login), `REPORT_TO` (where the update goes — you).
4. **Actions → UTC standings → Run workflow** once to prove it. The first run creates `docs/standings.json`, a report and the ladder PNG.

## How the week works
- 04:00 AEST daily: standings refresh from live feeds.
- 14:00 Melbourne Tuesday: report built, ladder image rendered, email sent to you with a **one-tap WhatsApp share link** — tap, choose the group, send. WhatsApp has no official way for software to post into a group, so that tap stays human.

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
`utc/sports.py` the 20 competitions · `utc/scoring.py` the points rules · `utc/engine.py` builds `docs/standings.json` · `utc/report.py` weekly text + PNG · `utc/send.py` email · `feeds/` adapters · `docs/index.html` the page.
