const fs = require("node:fs");
const path = require("node:path");
const { ChatManager } = require(path.resolve(__dirname, "../../../desktop/app/chat.cjs"));
const {
  questionRelevancePrompt,
  validateQuestionRelevance,
} = require(path.resolve(__dirname, "../../../desktop/app/evidence.cjs"));

const [inputPath, outputPath] = process.argv.slice(2);
if (!inputPath || !outputPath) {
  console.error("Usage: node run-question-claim-relevance-replay-v0.1.cjs INPUT_PRIVATE_JSON OUTPUT_PRIVATE_JSON");
  process.exit(2);
}

const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));
if (!Array.isArray(input.rows) || input.schema_version !== "e007-fallback30-private-result-v0.1") {
  throw new Error("Select the private JSON produced by checkpoint 7R.");
}

const home = process.env.HOME;
const resources = "/Applications/Pocket i.app/Contents/Resources";
const chat = new ChatManager({
  executable: path.join(resources, "runtime/llama-cli"),
  modelPath: path.join(home, "Library/Application Support/pocket-i-desktop/models/Qwen3-8B-Q4_K_M.gguf"),
  timeoutMs: 600000,
});

const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
})[character]);

function stage(row, name) {
  return (row.stages || []).find((item) => item.stage === name)?.details || null;
}

function groundedCandidates(row) {
  const checked = stage(row, "evidence_id_check");
  const grounded = stage(row, "grounded_evidence");
  const acceptedIds = new Set(grounded?.accepted_ids || []);
  return (checked?.accepted || []).filter((item) => acceptedIds.has(item.candidate_id));
}

function writePrivate(output, rows) {
  const temporary = `${output}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify({
    schema_version: "e007-question-claim-relevance-private-result-v0.1",
    source_result: inputPath,
    rows,
  }, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temporary, output);
}

(async () => {
  const rows = [];
  for (const [index, row] of input.rows.entries()) {
    const candidates = groundedCandidates(row);
    process.stdout.write(`[${index + 1}/30] ${candidates.length ? `${candidates.length} grounded claim(s)` : "no grounded claims"}\n`);
    if (!candidates.length) {
      rows.push({ number: row.number, group: row.group, question: row.question, expected: row.expected, status: "not_run_no_grounded_claims", candidates: [] });
      writePrivate(outputPath, rows);
      continue;
    }
    const raw = await chat.runPrompt(
      questionRelevancePrompt(row.question, candidates),
      row.question,
      512,
      "You classify whether grounded claims answer a question. Return only valid JSON.",
    );
    const result = validateQuestionRelevance(raw.answer, candidates);
    rows.push({
      number: row.number,
      group: row.group,
      question: row.question,
      expected: row.expected,
      status: result.valid ? "classified" : "invalid_output",
      candidates: candidates.map((candidate) => ({ candidate_id: candidate.candidate_id, claim: candidate.claim })),
      raw_answer: raw.answer,
      decisions: result.decisions,
      kept_ids: result.accepted.map((item) => item.candidate_id),
      dropped_ids: result.rejected.map((item) => item.candidate_id),
      error: result.reason,
    });
    writePrivate(outputPath, rows);
  }

  const htmlPath = outputPath.replace(/\.json$/i, ".html");
  const classified = rows.filter((row) => row.status !== "not_run_no_grounded_claims");
  fs.writeFileSync(htmlPath, `<!doctype html><meta charset="utf-8"><title>Pocket i · question relevance replay</title>
<style>body{font:18px system-ui;background:#f7f5ef;color:#191815;margin:0;padding:28px}main{max-width:1500px;margin:auto}article{border-top:2px solid #333;padding:24px 0}.claim{display:grid;grid-template-columns:120px 1fr 180px;gap:16px;padding:14px;border:1px solid #bbb}.answers,.contributes{background:#e5f6e8}.unrelated{background:#ffe7e2}.invalid_output{background:#fff0bd}code{font-size:16px}p{line-height:1.45}</style><main>
<h1>PRIVATE · Question ↔ claim relevance</h1><p>Only ${classified.length} questions contained claims that DeBERTa had already grounded. Check every decision with your own eyes.</p>
${classified.map((row) => `<article class="${escapeHtml(row.status)}"><h2>${escapeHtml(row.number)} · ${escapeHtml(row.question)}</h2><p><b>Expected answer:</b> ${escapeHtml(row.expected ?? "NO SUPPORTED ANSWER")}</p>${row.candidates.map((candidate) => { const decision = row.decisions.find((item) => item.candidate_id === candidate.candidate_id)?.relation || "INVALID"; return `<div class="claim ${escapeHtml(decision)}"><code>${escapeHtml(candidate.candidate_id)}</code><div>${escapeHtml(candidate.claim)}</div><b>${escapeHtml(decision.toUpperCase())}</b></div>`; }).join("")}</article>`).join("")}
</main>`, { mode: 0o600 });
  console.log(`PRIVATE_JSON: ${outputPath}`);
  console.log(`PRIVATE_HTML: ${htmlPath}`);
  require("node:child_process").spawn("open", [htmlPath], { detached: true, stdio: "ignore" }).unref();
})().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
