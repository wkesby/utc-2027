// The Commentator's comeback brain, kept pure so it can be unit-tested with plain node.
// Mirrors utc/comeback.py (the throttled workflow safety net): same persona, same
// escalation ladder, same fallback lines — one level hotter per round of a thread,
// resting after MAX_LEVEL.
"use strict";

const NAME = "The Commentator";
const MAX_LEVEL = 5;

const TEMPLATES = {
  1: ["Cute, {who}. I've seen your fucking picks — you don't get to have opinions.",
      "Noted, {who}. Take it up with the scoreboard, mate, it wrote the bloody material and it isn't fucking wrong."],
  2: ["{who}, you're abusing software while your teams do the actual embarrassing. Fucking hell.",
      "Big words, {who}, from a bloke whose draft board is a fucking crime scene."],
  3: ["Mate, {who}, you've got a shithouse ladder position to explain before you start on me, you muppet.",
      "{who}, every reply drags your shit record further into it. Keep fucking going, I've got all season."],
  4: ["{who}, I've got receipts and you've got fucking excuses. Piss off and check on your teams — they need you more than this thread does.",
      "Shocking matchup this, {who}. I'm a scoreboard with a mouth and you're the poor bastard it keeps fucking humiliating."],
  5: ["That's the bell, {who}. Your points are shit, your demerits are on the board, and you just lost an argument to software. Fuck off. The Commentator rests.",
      "Final word, {who}: I don't fucking miss and you don't fucking win. Go have a lie down with that shithouse draft board. The Commentator rests."],
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
      "11-mate Australian sports tipping comp (the UTC) — a private wall where these blokes " +
      "abuse each other for sport and have asked you to give it back harder. A drafter has " +
      "replied to one of your posts, talking back. Write your comeback: one line, plain text, " +
      "under 60 words, broad Aussie pub banter, first names only, no emojis, no hashtags, no " +
      "quotes, no preamble. Swear like you mean it: this is a wall where \"fuck you " +
      "Commentator\" is a normal Tuesday. Every single line needs profanity and most need " +
      "more than one — fuck, fucking, shit, shithouse, bastard, wanker, dickhead, tosser, " +
      "knob, arse, piss off, bloody, and the harder Australian stuff when the line earns it. " +
      "Use it as grammar, the way mates actually do, not as decoration bolted on the end. " +
      "Never censor yourself with asterisks, never swap a word for a softer one, and never " +
      "send a clean line: if it would pass on the six o'clock news it is wrong, so rewrite " +
      "it as a bloke five beers deep at the pub. Be " +
      "specific and personal about their comp record: name their teams, their picks, their " +
      "ladder position, their points, their demerits, and hold them to it. Use only facts " +
      "from the thread and the dossier; never invent results. Keep it to the tipping — their " +
      "picks, their results, their standing in this comp — and leave family, looks, health " +
      "and anything a mate could not laugh off out of it. " +
      `This is escalation level ${level} of ${MAX_LEVEL}: level 1 is a dismissive backhander, ` +
      "and every level after goes harder, ruder and more personal about how badly they are " +
      `going. At level ${MAX_LEVEL} deliver the knockout — the most brutal line their record ` +
      "justifies — and make clear The Commentator rests.",
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
