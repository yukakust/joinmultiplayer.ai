const http = require("node:http");
const https = require("node:https");

function requestJson(baseUrl, route, { method = "GET", payload = null, timeoutMs = 600000 } = {}) {
  const target = new URL(route, baseUrl);
  const client = target.protocol === "https:" ? https : http;
  const body = payload === null ? null : Buffer.from(JSON.stringify(payload));
  return new Promise((resolve, reject) => {
    const request = client.request(target, {
      method,
      timeout: timeoutMs,
      headers: body ? { "Content-Type": "application/json", "Content-Length": body.length } : {},
    }, (response) => {
      let value = "";
      response.setEncoding("utf8");
      response.on("data", (chunk) => { value += chunk; });
      response.on("end", () => {
        if (response.statusCode < 200 || response.statusCode >= 300) {
          reject(new Error(`Yukabox returned HTTP ${response.statusCode}.`));
          return;
        }
        try { resolve(JSON.parse(value)); } catch { reject(new Error("Yukabox returned invalid data.")); }
      });
    });
    request.on("timeout", () => request.destroy(new Error("Yukabox took too long to answer.")));
    request.on("error", () => reject(new Error("Yukabox brain is offline or unreachable.")));
    if (body) request.write(body);
    request.end();
  });
}

async function remoteChatCompletion(baseUrl, { prompt, systemPrompt, outputTokens, timeoutMs }) {
  const response = await requestJson(baseUrl, "/v1/chat/completions", {
    method: "POST",
    timeoutMs,
    payload: {
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: prompt },
      ],
      temperature: 0.2,
      max_tokens: outputTokens,
      stream: false,
      chat_template_kwargs: { enable_thinking: false },
    },
  });
  const answer = String(response?.choices?.[0]?.message?.content || "").trim();
  if (!answer) throw new Error("Yukabox returned no answer.");
  return { answer };
}

async function remoteHealth(baseUrl, timeoutMs = 3000) {
  try {
    await requestJson(baseUrl, "/health", { timeoutMs });
    return true;
  } catch {
    return false;
  }
}

module.exports = { remoteChatCompletion, remoteHealth, requestJson };
