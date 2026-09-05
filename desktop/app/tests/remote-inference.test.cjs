const assert = require("node:assert/strict");
const http = require("node:http");
const test = require("node:test");

const { remoteChatCompletion, remoteHealth } = require("../remote-inference.cjs");

async function fixtureServer() {
  let received = null;
  const routes = [];
  const authorizations = [];
  const server = http.createServer((request, response) => {
    routes.push(request.url);
    authorizations.push(request.headers.authorization || null);
    if (request.url.endsWith("/health")) {
      response.writeHead(200, { "Content-Type": "application/json" });
      response.end('{"status":"ok"}');
      return;
    }
    let body = "";
    request.on("data", (chunk) => { body += chunk; });
    request.on("end", () => {
      received = JSON.parse(body);
      response.writeHead(200, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ choices: [{ message: { content: "Remote answer" } }] }));
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return {
    baseUrl: `http://127.0.0.1:${server.address().port}`,
    received: () => received,
    routes,
    authorizations,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

test("checks the private remote brain and returns one clean answer", async () => {
  const server = await fixtureServer();
  try {
    assert.equal(await remoteHealth(server.baseUrl), true);
    const result = await remoteChatCompletion(server.baseUrl, {
      prompt: "Question",
      systemPrompt: "Identity",
      outputTokens: 64,
      timeoutMs: 5000,
    });
    assert.deepEqual(result, { answer: "Remote answer" });
    assert.equal(server.received().messages[0].content, "Identity");
    assert.equal(server.received().messages[1].content, "Question");
    assert.equal(server.received().chat_template_kwargs.enable_thinking, false);
  } finally {
    await server.close();
  }
});

test("keeps the HTTPS gateway lane and sends its private bearer token", async () => {
  const server = await fixtureServer();
  const baseUrl = `${server.baseUrl}/reader`;
  try {
    assert.equal(await remoteHealth(baseUrl, 5000, "closed-alpha-token"), true);
    await remoteChatCompletion(baseUrl, {
      prompt: "Question",
      systemPrompt: "Identity",
      outputTokens: 32,
      timeoutMs: 5000,
      accessToken: "closed-alpha-token",
    });
    assert.deepEqual(server.routes, ["/reader/health", "/reader/v1/chat/completions"]);
    assert.deepEqual(server.authorizations, ["Bearer closed-alpha-token", "Bearer closed-alpha-token"]);
  } finally {
    await server.close();
  }
});

test("reports an unreachable remote brain without leaking network details", async () => {
  assert.equal(await remoteHealth("http://127.0.0.1:1", 100), false);
});
