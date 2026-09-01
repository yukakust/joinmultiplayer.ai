const path = require("node:path");
const fs = require("node:fs/promises");
const manifest = require("./nli-manifest.json");
const { downloadVerified, sha256 } = require("./setup.cjs");

async function ready(item, destination) {
  try {
    const stat = await fs.stat(destination);
    return stat.size === item.bytes && await sha256(destination) === item.sha256;
  } catch {
    return false;
  }
}

async function main() {
  const root = path.join(__dirname, "nli-current");
  for (const item of manifest.files) {
    const destination = path.join(root, item.file);
    if (await ready(item, destination)) continue;
    process.stdout.write(`Preparing ${manifest.id}: ${item.file}\n`);
    await downloadVerified({ item, destination });
  }
  process.stdout.write(`NLI_READY: ${root}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
