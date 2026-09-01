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
const memoryConnect = document.querySelector("#memory-connect");
const memoryConsent = document.querySelector("#memory-consent");
const memoryConfirm = document.querySelector("#memory-confirm");
const memoryCancel = document.querySelector("#memory-cancel");
const memoryProgress = document.querySelector("#memory-progress");
let memoryReady = false;
let memoryBuilding = false;
let memoryStartedAt = null;
let latestMemoryProgress = null;
let memoryClock = null;

function elapsedMemory() {
  if (!memoryStartedAt) return "0:00";
  const seconds = Math.max(0, Math.floor((Date.now() - memoryStartedAt) / 1000));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function paintMemoryProgress() {
  if (!latestMemoryProgress) return;
  const elapsed = elapsedMemory();
  if (latestMemoryProgress.phase === "reading") {
    memoryProgress.textContent = `Reading conversations · ${elapsed}`;
  } else if (latestMemoryProgress.phase === "indexing") {
    memoryProgress.textContent = `Indexing ${latestMemoryProgress.completed.toLocaleString()} / ${latestMemoryProgress.total.toLocaleString()} messages · ${elapsed}`;
  } else if (latestMemoryProgress.phase === "ready") {
    memoryProgress.textContent = `Memory ready · ${elapsed}`;
  }
}

window.pocketI.onMemoryProgress((progress) => {
  latestMemoryProgress = progress;
  paintMemoryProgress();
});

function size(value) {
  return `${(value / 1024 ** 3).toFixed(1)} GB`;
}

function showCounts(library) {
  const counts = Object.fromEntries(
    library.adapters.map((adapter) => [adapter.source, adapter.conversations]),
  );
  libraryDetail.textContent = `Codex ${counts.codex || 0} · Claude ${counts.claude_code || 0}`;
}

async function renderMemoryStatus() {
  const memory = await window.pocketI.memoryStatus();
  if (memory.connected) {
    libraryStatus.textContent = memory.total_conversations ? "READY" : "EMPTY";
    showCounts(memory);
    memoryConnect.hidden = Boolean(memory.total_conversations);
    memoryReady = Boolean(memory.total_conversations);
    return;
  }
  libraryStatus.textContent = "NOT CONNECTED";
  libraryDetail.textContent = "Codex 0 · Claude 0";
  memoryConnect.hidden = false;
  memoryReady = false;
}

async function renderStatus() {
  const status = await window.pocketI.setupStatus();
  runtimeStatus.textContent = status.runtime.installed ? "READY" : "MISSING";
  if (status.readyToAsk) {
    modelStatus.textContent = "READY";
    setupView.hidden = true;
    chatView.hidden = false;
    await renderMemoryStatus();
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
    libraryStatus.textContent = "WAITING";
    memoryConnect.hidden = true;
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

memoryConnect.addEventListener("click", () => {
  chatView.hidden = true;
  memoryConsent.hidden = false;
  memoryProgress.hidden = true;
  if (memoryBuilding) {
    memoryProgress.hidden = false;
    memoryCancel.textContent = "BACK TO CHAT";
    paintMemoryProgress();
  }
});

memoryCancel.addEventListener("click", () => {
  memoryConsent.hidden = true;
  chatView.hidden = false;
  chatInput.focus();
});

memoryConfirm.addEventListener("click", async () => {
  memoryConfirm.disabled = true;
  memoryCancel.textContent = "BACK TO CHAT";
  memoryProgress.hidden = false;
  memoryBuilding = true;
  memoryStartedAt = Date.now();
  latestMemoryProgress = { phase: "reading" };
  memoryClock = setInterval(paintMemoryProgress, 1000);
  errorBox.hidden = true;
  try {
    libraryStatus.textContent = "FINDING";
    memoryProgress.textContent = "Finding Codex and Claude conversations…";
    const found = await window.pocketI.scan();
    showCounts(found);
    libraryStatus.textContent = "BUILDING";
    memoryProgress.textContent = "Building local memory…";
    const connected = await window.pocketI.connectMemory();
    showCounts(connected);
    libraryStatus.textContent = connected.total_conversations ? "READY" : "EMPTY";
    memoryConnect.hidden = Boolean(connected.total_conversations);
    memoryReady = Boolean(connected.total_conversations);
    memoryBuilding = false;
    memoryConsent.hidden = true;
    chatView.hidden = false;
    chatInput.focus();
  } catch (error) {
    memoryBuilding = false;
    libraryStatus.textContent = "FAILED";
    memoryProgress.textContent = error.message || "Memory could not be connected.";
  } finally {
    clearInterval(memoryClock);
    memoryClock = null;
    memoryConfirm.disabled = false;
    memoryCancel.textContent = "NOT NOW";
  }
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

function addRouteResults(result) {
  const list = document.createElement("section");
  list.className = "route-results";
  const heading = document.createElement("strong");
  heading.textContent = `Found ${result.returned} conversations`;
  list.append(heading);
  for (const item of result.items) {
    const card = document.createElement("article");
    const label = document.createElement("small");
    label.textContent = `${item.rank} · ${item.source === "claude_code" ? "CLAUDE" : "CODEX"} · ${item.messages} MESSAGES`;
    const preview = document.createElement("p");
    preview.textContent = item.preview;
    card.append(label, preview);
    list.append(card);
  }
  messages.append(list);
  messages.scrollTop = messages.scrollHeight;
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
    if (memoryReady) {
      pending.textContent = "Searching memory…";
      const result = await window.pocketI.routeMemory(question);
      pending.remove();
      addRouteResults(result);
      return;
    }
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
