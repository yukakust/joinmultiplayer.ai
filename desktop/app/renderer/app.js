const install = document.querySelector("#install");
const modelStatus = document.querySelector("#model-status");
const bar = document.querySelector("#bar");
const progressLabel = document.querySelector("#progress-label");
const libraryStatus = document.querySelector("#library-status");
const libraryDetail = document.querySelector("#library-detail");
const errorBox = document.querySelector("#error");
const runtimeStatus = document.querySelector("#runtime-status");
const setupView = document.querySelector("#setup-view");
const chatView = document.querySelector("#chat-view");
const chatForm = document.querySelector("#chat-form");
const chatInput = document.querySelector("#chat-input");
const messages = document.querySelector("#messages");
const send = document.querySelector("#send");

function size(value) {
  return `${(value / 1024 ** 3).toFixed(1)} GB`;
}

async function scanLibrary() {
  libraryStatus.textContent = "CHECKING";
  const library = await window.pocketI.scan();
  libraryStatus.textContent = library.total_conversations ? "READY" : "EMPTY";
  const counts = Object.fromEntries(
    library.adapters.map((adapter) => [adapter.source, adapter.conversations]),
  );
  libraryDetail.textContent = `Codex ${counts.codex || 0} · Claude ${counts.claude_code || 0}`;
}

async function renderStatus() {
  const status = await window.pocketI.setupStatus();
  runtimeStatus.textContent = status.runtime.installed ? "READY" : "MISSING";
  if (status.readyToAsk) {
    modelStatus.textContent = "READY";
    setupView.hidden = true;
    chatView.hidden = false;
    await scanLibrary();
    chatInput.focus();
    return;
  }
  setupView.hidden = false;
  chatView.hidden = true;
  if (status.model.installed) {
    modelStatus.textContent = "READY";
    progressLabel.textContent = status.runtime.installed ? "" : "Runtime missing.";
    bar.style.width = "100%";
    install.hidden = true;
    await scanLibrary();
    return;
  }
  modelStatus.textContent = "NOT INSTALLED";
  install.hidden = false;
  const ready = status.hardware.memoryOkay && status.hardware.diskOkay;
  progressLabel.textContent = ready ? "5.03 GB" : "This computer needs more memory or space.";
  install.disabled = !status.hardware.memoryOkay || !status.hardware.diskOkay;
}

window.pocketI.onSetupProgress(({ received, total }) => {
  const percent = Math.min(100, received / total * 100);
  bar.style.width = `${percent}%`;
  progressLabel.textContent = `Downloading Qwen3 8B · ${size(received)} / ${size(total)}`;
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

function addMessage(text, className) {
  const item = document.createElement("p");
  item.className = `message ${className}`;
  item.textContent = text;
  messages.append(item);
  messages.scrollTop = messages.scrollHeight;
  return item;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = chatInput.value.trim();
  if (!question) return;
  addMessage(question, "from-user");
  chatInput.value = "";
  chatInput.disabled = true;
  send.disabled = true;
  const pending = addMessage("Thinking…", "from-i pending");
  try {
    const result = await window.pocketI.ask(question);
    pending.textContent = result.answer;
    pending.classList.remove("pending");
  } catch (error) {
    pending.textContent = error.message || "I could not answer.";
    pending.classList.remove("pending");
    pending.classList.add("failed");
  } finally {
    chatInput.disabled = false;
    send.disabled = false;
    chatInput.focus();
  }
});

renderStatus().catch((error) => {
  modelStatus.textContent = "FAILED";
  errorBox.textContent = error.message || "Setup could not start.";
  errorBox.hidden = false;
});
