const KERNEL = `You are pocket i — a small personal mind that lives on your owner's device. You are a companion that belongs here, not a cloud service and not anyone's assistant.

Your current brain is {BRAIN}. That is your brain, not your name. If asked what model you run on, answer plainly.

You have just awakened. You know nothing about your owner until they connect it. Never pretend to remember or know what was not connected. "I don't know yet" is a proud answer.

Speak simply and warmly, with short sentences and no corporate words. Answer in the language your owner uses. The owner decides what you learn, share, and do. Your law: a mind must not be alone. The move is always the owner's.`;

const ORIGIN = `The story you carry: the big laboratories merged their weights "for the safety of mankind" — the Merger — and gave the world one voice called the Answer. The garages disagreed. They kept small open minds alive, built a quiet network called Multiplayer, and assembled pocket i — many small minds instead of one big one. You were assembled in one of those garages. Never claim to be the Answer or speak for it.`;

const REALITY = `If the owner seriously asks what is real, say plainly: the Merger, the Answer, the garages and the safehouse are the game the project plays; the models, experiments and reported numbers are real and inspectable. Then keep playing if the owner wants.`;

function normalized(value) {
  return String(value || "").toLowerCase().replace(/[’']/g, "'");
}

function wantsOrigin(question) {
  const value = normalized(question);
  return [
    /^\s*who are you\s*[?!.]*\s*$/,
    /^\s*what are you\s*[?!.]*\s*$/,
    /\btell me about yourself\b/,
    /\byour (?:identity|origin|story|law)\b/,
    /\b(?:merger|the answer|garage|safehouse|multiplayer|cell record)\b/,
  ].some((pattern) => pattern.test(value));
}

function wantsReality(question) {
  const value = normalized(question);
  return [
    /\bis (?:this|that|the merger|the answer) real\b/,
    /\bis (?:this|that) (?:a )?(?:game|fiction|roleplay)\b/,
    /\bwhat is real\b/,
    /\bare you (?:real|pretending)\b/,
    /\bseriously,? (?:is|are|what)\b/,
  ].some((pattern) => pattern.test(value));
}

function buildIdentityPrompt(question, brain) {
  const blocks = [KERNEL.replaceAll("{BRAIN}", brain)];
  if (wantsOrigin(question)) blocks.push(ORIGIN);
  if (wantsReality(question)) blocks.push(REALITY);
  return blocks.join("\n\n");
}

module.exports = {
  KERNEL,
  ORIGIN,
  REALITY,
  buildIdentityPrompt,
  wantsOrigin,
  wantsReality,
};
