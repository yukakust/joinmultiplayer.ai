const SECRET_PATTERNS = [
  ["openai_key", /\bsk-[A-Za-z0-9_-]{16,}\b/],
  ["github_token", /\b(?:ghp|github_pat)_[A-Za-z0-9_]{16,}\b/i],
  ["slack_token", /\bxox[baprs]-[A-Za-z0-9-]{10,}\b/i],
  ["aws_key", /\bAKIA[0-9A-Z]{16}\b/],
  ["private_key", /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/],
  ["bearer_token", /\bauthorization\s*[:=]\s*bearer\s+[^\s,;]+/i],
  ["named_secret", /\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password)\s*[:=]\s*[^\s,;]{8,}/i],
];

function secretCategories(value) {
  const text = String(value || "");
  return SECRET_PATTERNS.filter(([, pattern]) => pattern.test(text)).map(([name]) => name);
}

module.exports = { secretCategories };
