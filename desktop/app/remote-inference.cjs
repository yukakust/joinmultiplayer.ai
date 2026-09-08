const http = require("node:http");
const https = require("node:https");

function requestOnce(target, { method = "GET", body = null, timeoutMs, accessToken = null, asyncJob = false }) {
  const client = target.protocol === "https:" ? https : http;
  const headers = body ? { "Content-Type": "application/json", "Content-Length": body.length } : {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  if (accessToken && method === "POST") headers["X-Pocket-I-Alpha-Audit"] = "full";
  if (accessToken && method === "POST" && asyncJob) headers["X-Pocket-I-Async"] = "v1";
  return new Promise((resolve, reject) => {
    const request = client.request(target, {
      method,
      timeout: timeoutMs,
      headers,
    }, (response) => {
      let value = "";
      response.setEncoding("utf8");
      response.on("data", (chunk) => { value += chunk; });
      response.on("end", () => {
        if (response.statusCode < 200 || response.statusCode >= 300) {
          reject(new Error(`Yukabox returned HTTP ${response.statusCode}.`));
          return;
        }
        try { resolve({ status: response.statusCode, value: JSON.parse(value) }); } catch { reject(new Error("Yukabox returned invalid data.")); }
      });
    });
    request.on("timeout", () => request.destroy(new Error("Yukabox took too long to answer.")));
    request.on("error", () => reject(new Error("Yukabox brain is offline or unreachable.")));
    if (body) request.write(body);
    request.end();
  });
}

function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function requestJson(baseUrl, route, { method = "GET", payload = null, timeoutMs = 600000, accessToken = null } = {}) {
  const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const normalizedRoute = String(route || "").replace(/^\/+/, "");
  const target = new URL(normalizedRoute, normalizedBase);
  const body = payload === null ? null : Buffer.from(JSON.stringify(payload));
  const started = Date.now();
  const first = await requestOnce(target, {
    method,
    body,
    timeoutMs,
    accessToken,
    asyncJob: method === "POST",
  });
  if (first.status !== 202 || !first.value?.job_id) return first.value;

  const jobId = String(first.value.job_id);
  const pollTarget = new URL(`/jobs/${encodeURIComponent(jobId)}`, target.origin);
  let state = first.value;
  while (["queued", "running"].includes(state?.state)) {
    const elapsed = Date.now() - started;
    if (elapsed >= timeoutMs) throw new Error("Yukabox took too long to answer.");
    await wait(Math.min(Number(state.poll_after_ms) || 1000, Math.max(1, timeoutMs - elapsed)));
    const remaining = Math.max(1, timeoutMs - (Date.now() - started));
    const polled = await requestOnce(pollTarget, {
      method: "GET",
      timeoutMs: Math.min(15000, remaining),
      accessToken,
    });
    state = polled.value;
  }
  if (state?.state === "failed") {
    throw new Error(`Yukabox returned HTTP ${Number(state.response_status) || 502}.`);
  }
  if (state?.state !== "ready" || !state.result) throw new Error("Yukabox returned invalid job data.");
  return state.result;
}

async function remoteChatCompletion(baseUrl, { prompt, systemPrompt, outputTokens, timeoutMs, accessToken = null }) {
  const response = await requestJson(baseUrl, "/v1/chat/completions", {
    method: "POST",
    timeoutMs,
    accessToken,
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

async function remoteHealth(baseUrl, timeoutMs = 3000, accessToken = null) {
  try {
    await requestJson(baseUrl, "/health", { timeoutMs, accessToken });
    return true;
  } catch {
    return false;
  }
}

module.exports = { remoteChatCompletion, remoteHealth, requestJson };
