const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildIdentityPrompt,
  wantsOrigin,
  wantsReality,
} = require("../identity.cjs");

test("ordinary work receives only the short identity kernel", () => {
  const prompt = buildIdentityPrompt("Explain why this test failed.", "Qwen3 8B");
  assert.match(prompt, /You are pocket i/);
  assert.match(prompt, /Qwen3 8B/);
  assert.doesNotMatch(prompt, /big laboratories merged/);
  assert.doesNotMatch(prompt, /game the project plays/);
  assert.ok(prompt.split(/\s+/).length < 130);
  assert.equal(wantsOrigin("What are you working on?"), false);
});

test("identity questions receive the origin without the reality disclosure", () => {
  assert.equal(wantsOrigin("Who are you?"), true);
  const prompt = buildIdentityPrompt("Who are you?", "Qwen3 8B");
  assert.match(prompt, /big laboratories merged/);
  assert.match(prompt, /many small minds/);
  assert.doesNotMatch(prompt, /game the project plays/);
  assert.ok(prompt.split(/\s+/).length < 220);
});

test("serious reality questions open the honest valve", () => {
  assert.equal(wantsReality("Is the Merger real?"), true);
  const prompt = buildIdentityPrompt("Is the Merger real?", "Qwen3 8B");
  assert.match(prompt, /game the project plays/);
  assert.match(prompt, /models, experiments and reported numbers are real/);
});

test("the brain label is data rather than a hardcoded identity", () => {
  const prompt = buildIdentityPrompt("What model do you run?", "Another Open Brain");
  assert.match(prompt, /Another Open Brain/);
  assert.doesNotMatch(prompt, /Qwen3 8B/);
});
