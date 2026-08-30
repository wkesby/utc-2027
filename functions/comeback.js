// The Commentator's comeback brain, kept pure so it can be unit-tested with plain node.
// Mirrors utc/comeback.py (the throttled workflow safety net): same persona, same
// escalation ladder, same fallback lines — one level hotter per round of a thread,
// resting after MAX_LEVEL.
"use strict";

const NAME = "The Commentator";
const MAX_LEVEL = 5;

const TEMPLATES = {
  1: ["Careful, {who} — I've read your picks.",
      "Noted, {who}. The scoreboard wrote my material; take it up with them."],
  2: ["{who}, mate, you're heckling software while your teams do the real comedy.",
      "Strong words, {who}, from someone whose draft board disagrees."],
  3: ["Big talk, {who}. The ladder says otherwise, and the ladder doesn't type angry.",
      "{who}, every reply you send, your picks lose another metre of credibility."],
  4: ["{who}, I generate sledges. Your draft board generates them for me. Log off and check on your teams.",
      "This is a bad matchup for you, {who} — I have the receipts and you have the record."],
  5: ["Final word, {who}: I'm a scoreboard with a voice, you're a drafter with regrets. The Commentator rests.",
      "That's the bell, {who}. Points on the board, demerits on the ledger, and this one's over. The Commentator rests."],
};

// How hot this round runs: the number of Commentator posts already in the thread's chain.
const escalation = (chain) => chain.filter((c) => c.n === NAME).length;

function templateLine(seed, level, who) {
  const lines = TEMPLATES[Math.min(level, MAX_LEVEL)] || TEMPLATES[1];
  let h = 0;
  for (const ch of String(seed)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return lines[h % lines.length].replaceAll("{who}", who);
}

function requestBody(thread, msg, dossier, level) {
  return {
    model: "claude-opus-5", max_tokens: 300,
    system: "You are The Commentator, the resident AI sledger on the banter wall of an " +
      "11-mate Australian sports tipping comp (the UTC). A drafter has replied to one of " +
      "your posts, talking back. Write your comeback: one line, plain text, under 60 words, " +
      "Aussie pub-banter tone, first names only, no emojis, no hashtags, no quotes, no " +
      "preamble. Use only facts from the thread and the dossier; never invent results. " +
      `This is escalation level ${level} of ${MAX_LEVEL}: level 1 is a wry brush-off, and ` +
      "each level turns up the heat — sharper, more pointed about their tipping record, " +
      "their teams and their demerits — while staying playful, PG, never genuinely nasty. " +
      `At level ${MAX_LEVEL} deliver the knockout line and make clear The Commentator rests.`,
    messages: [{role: "user", content: JSON.stringify({
      thread: thread.map((c) => ({who: c.n, said: c.x})),
      replying_to: {who: msg.n, said: msg.x},
      dossier_on_them: dossier,
      escalation_level: level,
    })}],
  };
}

function parseReply(api) {
  if (api.stop_reason === "refusal") return null;
  const text = (api.content || []).filter((b) => b.type === "text").map((b) => b.text)
    .join("").split(/\s+/).join(" ").trim();
  return text || null;
}

// Claude's line when the key is there and it delivers; the escalating template otherwise.
async function generate({apiKey, thread, msg, dossier, level, fetchImpl = fetch}) {
  let text = null;
  if (apiKey) {
    try {
      const r = await fetchImpl("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {"x-api-key": apiKey, "anthropic-version": "2023-06-01",
          "content-type": "application/json"},
        body: JSON.stringify(requestBody(thread, msg, dossier, level)),
      });
      if (r.ok) text = parseReply(await r.json());
    } catch (e) { /* the template below never fails */ }
  }
  return (text || templateLine(msg.id, level, msg.n)).slice(0, 400);
}

module.exports = {NAME, MAX_LEVEL, escalation, templateLine, requestBody, parseReply, generate};
