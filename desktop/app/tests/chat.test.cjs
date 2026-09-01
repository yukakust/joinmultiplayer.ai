const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { ChatManager } = require("../chat.cjs");

test("returns one clean local answer", { skip: process.platform === "win32" }, async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "pocket-i-chat-"));
  const executable = path.join(directory, "fake-llama-cli");
  await fs.writeFile(executable, "#!/usr/bin/env node\nprocess.stdout.write('\\u001b[31mFixture answer\\u001b[0m\\n')\n", { mode: 0o700 });
  const chat = new ChatManager({ executable, modelPath: path.join(directory, "model.gguf"), timeoutMs: 5000 });
  assert.deepEqual(await chat.ask("Hello"), { answer: "Fixture answer" });
});

test("rejects empty and oversized questions before inference", async () => {
  const chat = new ChatManager({ executable: "unused", modelPath: "unused" });
  await assert.rejects(chat.ask("  "), /question/);
  await assert.rejects(chat.ask("x".repeat(4001)), /4,000/);
});
