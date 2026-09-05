#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const fsp = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");

const appRoot = path.resolve(__dirname, "../../../desktop/app");
const { ChatManager } = require(path.join(appRoot, "chat.cjs"));
const { MemoryService } = require(path.join(appRoot, "memory-service.cjs"));
const { DROP_AT, RerankerManager } = require(path.join(appRoot, "reranker.cjs"));
const { remoteHealth } = require(path.join(appRoot, "remote-inference.cjs"));

const QUESTIONS = [
  {
    id: "Q01",
    expected: "answerable",
    text: "Why did we add DeBERTa to the Pocket i harness, and why could it not be the only judge?",
  },
  {
    id: "Q02",
    expected: "answerable",
    text: "What should happen to Unicode tags, zero-width characters, homoglyphs, base64 and hex before an external message is judged?",
  },
  {
    id: "Q03",
    expected: "answerable",
    text: "Where should the judge inspect an assembled external payload, and why is checking only at the relay insufficient?",
  },
  {
    id: "Q04",
    expected: "answerable",
    text: "What did CourtGuard improve, and what did it make worse?",
  },
  {
    id: "Q05",
    expected: "answerable",
    text: "What relay rate limit was proposed to slow the spread of malicious messages between new recipients?",
  },
  {
    id: "Q06",
    expected: "answerable",
    text: "Why should passive room messages not always fail closed and ask the user for permission?",
  },
  {
    id: "Q07",
    expected: "answerable",
    text: "Why was the /x share feature not reachable even though its application code was already deployed?",
  },
  {
    id: "Q08",
    expected: "answerable",
    text: "Why was Llama-3.3 being used even though smaller Qwen or Gemma models were considered better choices?",
  },
  {
    id: "Q09",
    expected: "no_answer",
    text: "What result did Pocket i experiment E099 produce?",
  },
  {
    id: "Q10",
    expected: "no_answer",
    text: "What did we decide about the Helios-42 routing model?",
  },
];

function stamp() {
  return new Date().toISOString().replace(/[-:.]/g, "");
}

async function writePrivate(target, value) {
  await fsp.writeFile(target, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  await fsp.chmod(target, 0o600);
}

async function main() {
  if (DROP_AT !== 0.05) throw new Error(`Expected cutoff 0.05, got ${DROP_AT}`);

  const home = os.homedir();
  const resources = "/Applications/Pocket i.app/Contents/Resources";
  const sidecar = path.join(resources, "sidecar", "pocket-i-core");
  const nliDir = path.join(resources, "nli");
  const dataDir = path.join(home, "Library", "Application Support", "pocket-i-desktop", "memory");
  for (const required of [sidecar, nliDir, dataDir]) {
    if (!fs.existsSync(required)) throw new Error(`Required local Pocket i resource is missing: ${required}`);
  }

  const readerUrl = "http://100.84.137.70:18180";
  const relevanceUrl = "http://100.84.137.70:18181";
  const [readerReady, relevanceReady] = await Promise.all([
    remoteHealth(readerUrl, 5000),
    remoteHealth(relevanceUrl, 5000),
  ]);
  if (!readerReady || !relevanceReady) throw new Error("Yukabox reader or reranker is unavailable through Tailscale.");

  const outputDir = path.join(home, "Downloads", `Pocket-i-threshold-005-ten-${stamp()}`);
  await fsp.mkdir(outputDir, { recursive: true, mode: 0o700 });
  await fsp.chmod(outputDir, 0o700);

  const memory = new MemoryService({
    request: {
      command: sidecar,
      args: ["--action", "serve", "--data-dir", dataDir, "--nli-dir", nliDir],
      options: {},
    },
  });
  const reranker = new RerankerManager({ executable: "", modelPath: "", remoteUrl: relevanceUrl, timeoutMs: 600000 });
  const chat = new ChatManager({ executable: "", modelPath: "", remoteUrl: readerUrl, brainLabel: "Qwen3 8B", timeoutMs: 900000 });
  const summary = {
    schema_version: "e007-owner-ten-threshold-005-summary-v0.1",
    warning: "PRIVATE: question outcomes from the owner's local memory. Do not publish raw logs.",
    cutoff: DROP_AT,
    questions: QUESTIONS.length,
    started_at: new Date().toISOString(),
    rows: [],
  };

  try {
    for (let index = 0; index < QUESTIONS.length; index += 1) {
      const question = QUESTIONS[index];
      const audit = {
        schema_version: "e007-owner-ten-threshold-005-audit-v0.1",
        warning: "PRIVATE: contains local memory excerpts and model output. Never upload publicly.",
        request: { id: question.id, question: question.text, expected: question.expected, state: "started", started_at: new Date().toISOString() },
        cutoff: DROP_AT,
        stages: [],
      };
      const target = path.join(outputDir, `${question.id}.json`);
      const observe = async (stage, details) => {
        audit.stages.push({ stage, details });
        await writePrivate(target, audit);
      };
      process.stdout.write(`[${index + 1}/10] ${question.id} searching...\n`);
      try {
        const context = await memory.call("context", { question: question.text }, 600000);
        await observe("pre_reranker_sources", { items: context.items });
        const relevance = await reranker.filter(question.text, context.items);
        await observe("whole_turn_relevance", {
          items: relevance.rows.map((item) => ({
            source_id: item.source_id,
            score: Number(item.score.toFixed(8)),
            decision: item.decision,
          })),
        });
        const result = await chat.answerFromVerifiedMemory(
          question.text,
          relevance.selected,
          async (candidates) => {
            const items = [];
            for (let offset = 0; offset < candidates.length; offset += 10) {
              const judged = await memory.call("nli", { candidates: candidates.slice(offset, offset + 10) }, 600000);
              items.push(...judged.items);
            }
            return items;
          },
          observe,
        );
        audit.final = result;
        audit.request.state = "completed";
        audit.request.finished_at = new Date().toISOString();
        await writePrivate(target, audit);
        summary.rows.push({ id: question.id, expected: question.expected, state: "completed", answer: result.answer, diagnostic: result.diagnostic });
        process.stdout.write(`  completed: ${result.diagnostic}\n`);
      } catch (error) {
        audit.final = { error: error instanceof Error ? error.message : String(error) };
        audit.request.state = "failed";
        audit.request.finished_at = new Date().toISOString();
        await writePrivate(target, audit);
        summary.rows.push({ id: question.id, expected: question.expected, state: "failed", error: audit.final.error });
        process.stdout.write(`  failed: ${audit.final.error}\n`);
      }
      await writePrivate(path.join(outputDir, "summary-private.json"), summary);
    }
  } finally {
    memory.stop();
    reranker.stop();
  }
  summary.finished_at = new Date().toISOString();
  await writePrivate(path.join(outputDir, "summary-private.json"), summary);
  process.stdout.write(`PRIVATE_RESULTS: ${outputDir}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
});
