const fs = require("node:fs/promises");
const path = require("node:path");
const { spawn } = require("node:child_process");
const manifest = require("./runtime-manifest.json");
const { downloadVerified } = require("./setup.cjs");

function run(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: "inherit", windowsHide: true });
    child.on("error", reject);
    child.on("close", (code) => code === 0 ? resolve() : reject(new Error(`${command} exited ${code}`)));
  });
}

async function main() {
  const key = `${process.platform}-${process.arch}`;
  const target = manifest.targets[key];
  if (!target) throw new Error(`No pinned llama.cpp runtime for ${key}.`);

  const root = __dirname;
  const build = path.join(root, "build-runtime");
  const output = path.join(root, "runtime-current");
  const archive = path.join(build, target.archive);
  await fs.rm(build, { recursive: true, force: true });
  await fs.rm(output, { recursive: true, force: true });
  await fs.mkdir(build, { recursive: true, mode: 0o700 });
  await fs.mkdir(output, { recursive: true, mode: 0o700 });
  await downloadVerified({ item: target, destination: archive });
  await run("tar", ["-xzf", archive, "-C", output, "--strip-components=1"]);
  const executable = path.join(output, target.executable);
  await fs.chmod(executable, 0o700);
  process.stdout.write(`RUNTIME_READY ${manifest.revision} ${key}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
