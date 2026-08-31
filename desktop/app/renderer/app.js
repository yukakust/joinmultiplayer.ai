const install = document.querySelector("#install");
const modelStatus = document.querySelector("#model-status");
const bar = document.querySelector("#bar");
const progressLabel = document.querySelector("#progress-label");
const libraryStatus = document.querySelector("#library-status");
const libraryDetail = document.querySelector("#library-detail");
const errorBox = document.querySelector("#error");

function size(value) {
  return `${(value / 1024 ** 3).toFixed(1)} GB`;
}

async function scanLibrary() {
  libraryStatus.textContent = "CHECKING";
  const library = await window.pocketI.scan();
  libraryStatus.textContent = library.total_conversations ? "READY" : "EMPTY";
  libraryDetail.textContent = `${library.total_conversations} conversations · ${library.total_messages} visible messages`;
}

async function renderStatus() {
  const status = await window.pocketI.setupStatus();
  if (status.model.installed) {
    modelStatus.textContent = "READY";
    progressLabel.textContent = "The model passed its size and checksum checks.";
    bar.style.width = "100%";
    install.hidden = true;
    await scanLibrary();
    return;
  }
  modelStatus.textContent = "NOT INSTALLED";
  install.hidden = false;
  const notes = [`Memory ${size(status.hardware.memoryBytes)}`, `Free ${size(status.hardware.freeBytes)}`];
  if (!status.hardware.memoryOkay) notes.push("12 GB memory required");
  if (!status.hardware.diskOkay) notes.push("8 GB free space required");
  progressLabel.textContent = notes.join(" · ");
  install.disabled = !status.hardware.memoryOkay || !status.hardware.diskOkay;
}

window.pocketI.onSetupProgress(({ received, total }) => {
  const percent = Math.min(100, received / total * 100);
  bar.style.width = `${percent}%`;
  progressLabel.textContent = `${size(received)} of ${size(total)}`;
});

install.addEventListener("click", async () => {
  install.disabled = true;
  modelStatus.textContent = "DOWNLOADING";
  errorBox.hidden = true;
  try {
    await window.pocketI.installModel();
    await renderStatus();
  } catch (error) {
    modelStatus.textContent = "FAILED";
    errorBox.textContent = error.message || "The model could not be installed.";
    errorBox.hidden = false;
    install.disabled = false;
  }
});

renderStatus().catch((error) => {
  modelStatus.textContent = "FAILED";
  errorBox.textContent = error.message || "Setup could not start.";
  errorBox.hidden = false;
});

