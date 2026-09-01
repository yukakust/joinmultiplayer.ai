const { spawn } = require("node:child_process");
const path = require("node:path");
const { buildIdentityPrompt } = require("./identity.cjs");

function cleanOutput(value) {
  return value.replace(/\u001b\[[0-9;]*m/g, "").trim();
}

function extractAnswer(value, prompt) {
  const output = cleanOutput(value).replace(/\r\n/g, "\n");
  const marker = `> ${prompt}`;
  const markerIndex = output.lastIndexOf(marker);
  const answer = markerIndex >= 0 ? output.slice(markerIndex + marker.length) : output;
  return answer.replace(/\n+\s*Exiting\.\.\.\s*$/, "").trim();
}

class ChatManager {
  constructor({ executable, modelPath, brainLabel = "Qwen3 8B", timeoutMs = 600000 }) {
    this.executable = executable;
    this.modelPath = modelPath;
    this.brainLabel = brainLabel;
    this.timeoutMs = timeoutMs;
    this.active = false;
  }

  ask(question) {
    const prompt = typeof question === "string" ? question.trim() : "";
    if (!prompt) return Promise.reject(new Error("Write a question first."));
    if (prompt.length > 4000) return Promise.reject(new Error("Keep the first question under 4,000 characters."));
    if (this.active) return Promise.reject(new Error("Pocket i is already thinking."));
    this.active = true;
    const args = [
      "-m", this.modelPath,
      "-p", prompt,
      "-sys", buildIdentityPrompt(prompt, this.brainLabel),
      "-n", "256",
      "--temp", "0.2",
      "--reasoning", "off",
      "--single-turn",
      "--simple-io",
      "--no-display-prompt",
      "--no-show-timings",
      "--no-warmup",
      "--log-disable",
      "--color", "off"
    ];
    const runtimeDirectory = path.dirname(this.executable);
    const env = {
      ...process.env,
      LD_LIBRARY_PATH: [runtimeDirectory, process.env.LD_LIBRARY_PATH].filter(Boolean).join(path.delimiter),
      DYLD_LIBRARY_PATH: [runtimeDirectory, process.env.DYLD_LIBRARY_PATH].filter(Boolean).join(path.delimiter),
    };

    return new Promise((resolve, reject) => {
      const child = spawn(this.executable, args, { env, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
      let stdout = "";
      let stderr = "";
      const done = () => { this.active = false; };
      const timer = setTimeout(() => {
        child.kill();
        done();
        reject(new Error("Pocket i took too long to answer."));
      }, this.timeoutMs);
      child.stdout.on("data", (chunk) => { stdout += chunk.toString(); });
      child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
      child.on("error", (error) => {
        clearTimeout(timer);
        done();
        reject(error);
      });
      child.on("close", (code) => {
        clearTimeout(timer);
        done();
        if (code !== 0) {
          reject(new Error(cleanOutput(stderr) || "The local model failed."));
          return;
        }
        const answer = extractAnswer(stdout, prompt);
        if (!answer) {
          reject(new Error("The local model returned no answer."));
          return;
        }
        resolve({ answer });
      });
    });
  }
}

module.exports = { ChatManager, cleanOutput, extractAnswer };
