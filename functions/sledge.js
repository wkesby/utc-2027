// The sledge patrol's brain, kept pure so it can be unit-tested with plain node.
// Mirrors utc/trashtalk.py: the same detection (a finished game where exactly one side
// is drafted and that side lost), the same persona prompt, the same canned fallbacks.
// The patrol overlays fresh ESPN scoreboard state onto the published fixtures, so a
// defeat is caught within minutes of full time instead of on GitHub's throttled cron.
"use strict";

const {parseReply} = require("./comeback");

const TEMPLATES = [
  "{who}'s {team} just lost {sf}-{sa} to {opp} — a team nobody at the draft even wanted. Says it all really.",
  "Nobody drafted {opp}. {opp} still beat {who}'s {team} {sa}-{sf}. Sit with that one, {who}.",
  "{comp} update: {team} {sf}, {opp} {sa}. Beaten by the undrafted mob. Thoughts are with {who} at this time.",
  "{who} spent a draft pick on {team}. {opp} cost nothing and just beat them {sa}-{sf}. The market has spoken.",
];

// Sports worth an ESPN call this pass: any game not yet final that is in play or
// kicked off inside the last 12 hours.
function candidates(fx, now) {
  const out = [];
  for (const [key, s] of Object.entries(fx.sports || {})) {
    if (!s.path) continue;
    const hot = (s.games || []).some((g) => {
      if (g.st === "post") return false;
      if (g.st === "in") return true;
      const t = Date.parse(g.d);
      return isFinite(t) && t <= now && now - t < 12 * 36e5;
    });
    if (hot) out.push({key, path: s.path});
  }
  return out;
}

// Finished games where a drafted team lost to an undrafted one, judged on the fresher
// of the scoreboard overlay and the baked snapshot. Head-to-head stays the drafters' own fight.
function beatsFrom(fx, live) {
  const out = [];
  for (const [key, s] of Object.entries(fx.sports || {})) {
    for (const g of s.games || []) {
      if (!!g.hd === !!g.ad) continue;
      const ov = ((live || {})[key] || {})[g.i];
      const src = ov && ov.state ? ov : {state: g.st || "pre", hs: g.hs, as: g.as};
      if (src.state !== "post") continue;
      const hs = parseFloat(src.hs), as = parseFloat(src.as);
      if (!isFinite(hs) || !isFinite(as)) continue;
      const home = !!g.hd;
      const mine = home ? hs : as, theirs = home ? as : hs;
      if (mine >= theirs) continue;
      out.push({id: g.i || `${g.d}|${g.h}|${g.a}`, date: g.d,
        drafter: home ? g.hd : g.ad,
        their_team: home ? g.h : g.a, beaten_by: home ? g.a : g.h,
        score_for: String(home ? src.hs : src.as),
        score_against: String(home ? src.as : src.hs),
        competition: (s.name || "").split(" (")[0]});
    }
  }
  return out;
}

function templateLine(seed, b) {
  let h = 0;
  for (const ch of String(seed)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return TEMPLATES[h % TEMPLATES.length]
      .replaceAll("{who}", b.drafter).replaceAll("{team}", b.their_team)
      .replaceAll("{opp}", b.beaten_by).replaceAll("{sf}", b.score_for)
      .replaceAll("{sa}", b.score_against).replaceAll("{comp}", b.competition);
}

function requestBody(b) {
  return {
    model: "claude-opus-5", max_tokens: 300,
    system: "You write one-line trash talk for the banter wall of an 11-mate Australian " +
      "sports tipping comp (the UTC: each drafter picked one team per competition). A " +
      "drafter's team has just been beaten by a team that nobody bothered to draft. Reply " +
      "with the sledge only: one line, plain text, under 50 words, PG, Aussie tone, first " +
      "name only, no emojis, no hashtags, no quotes, no preamble. Use only the facts " +
      "given; never invent details.",
    messages: [{role: "user", content: JSON.stringify({
      drafter: b.drafter, their_team: b.their_team, beaten_by: b.beaten_by,
      score_for: b.score_for, score_against: b.score_against, competition: b.competition,
    })}],
  };
}

async function generate({apiKey, beat, fetchImpl = fetch}) {
  let text = null;
  if (apiKey) {
    try {
      const r = await fetchImpl("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {"x-api-key": apiKey, "anthropic-version": "2023-06-01",
          "content-type": "application/json"},
        body: JSON.stringify(requestBody(beat)),
      });
      if (r.ok) text = parseReply(await r.json());
    } catch (e) { /* the template below never fails */ }
  }
  return (text || templateLine(beat.id, beat)).slice(0, 400);
}

module.exports = {candidates, beatsFrom, templateLine, requestBody, generate};
