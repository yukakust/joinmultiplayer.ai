const install = document.querySelector("#install");
const modelStatus = document.querySelector("#model-status");
const bar = document.querySelector("#bar");
const progressLabel = document.querySelector("#progress-label");
const libraryStatus = document.querySelector("#library-status");
const libraryDetail = document.querySelector("#library-detail");
const errorBox = document.querySelector("#error");
const runtimeStatus = document.querySelector("#runtime-status");
const rerankerStatus = document.querySelector("#reranker-status");
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
const openTestLog = document.querySelector("#open-test-log");
const remoteConsent = document.querySelector("#remote-consent");
const remoteConfirm = document.querySelector("#remote-confirm");
const remoteCancel = document.querySelector("#remote-cancel");
const remoteBrainToggle = document.querySelector("#remote-brain-toggle");
const privacyNote = document.querySelector("#privacy-note");
let remoteConsented = false;
let remoteConsentDismissed = false;
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

openTestLog.addEventListener("click", async () => {
  try {
    await window.pocketI.openTestLog();
  } catch (error) {
    errorBox.textContent = error.message || "The private test log folder could not be opened.";
    errorBox.hidden = false;
  }
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
  const remote = status.mode === "remote";
  remoteConsented = Boolean(status.remoteConsented);
  remoteBrainToggle.hidden = !remote;
  remoteBrainToggle.textContent = remoteConsented ? "STOP USING YUKA’S SERVER" : "USE YUKA’S SERVER";
  remoteBrainToggle.classList.toggle("on", remoteConsented);
  privacyNote.textContent = remoteConsented
    ? "Selected excerpts may go to Yuka’s yukabox through Tailscale."
    : "Remote brain is off. Nothing is sent to yukabox.";
  runtimeStatus.textContent = status.runtime.installed ? "READY" : "MISSING";
  rerankerStatus.textContent = status.relevance?.installed ? "READY" : "NOT INSTALLED";
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
  if (remote) {
    if (status.consentRequired) {
      modelStatus.textContent = "OFF";
      rerankerStatus.textContent = "OFF";
      runtimeStatus.textContent = "OFF";
      progressLabel.textContent = "Yuka’s server is selected. No local model download is needed.";
      bar.style.width = "0%";
      install.textContent = "USE YUKA’S SERVER";
      install.hidden = false;
      install.disabled = false;
      if (!remoteConsentDismissed) {
        setupView.hidden = true;
        remoteConsent.hidden = false;
      }
      return;
    }
    modelStatus.textContent = status.model.installed ? "CONNECTED" : "OFFLINE";
    rerankerStatus.textContent = status.relevance?.installed ? "CONNECTED" : "OFFLINE";
    runtimeStatus.textContent = status.runtime.installed ? "TAILSCALE" : "OFFLINE";
    progressLabel.textContent = status.readyToAsk ? "Yukabox brain connected." : "Connect to Tailscale and wake yukabox.";
    bar.style.width = status.readyToAsk ? "100%" : "0%";
    install.textContent = "CONNECT YUKABOX";
    install.hidden = false;
    install.disabled = false;
    return;
  }
  if (status.model.installed && status.relevance?.installed) {
    modelStatus.textContent = "READY";
    progressLabel.textContent = status.runtime.installed ? "" : "Runtime missing.";
    bar.style.width = "100%";
    install.hidden = true;
    libraryStatus.textContent = "WAITING";
    memoryConnect.hidden = true;
    return;
  }
  modelStatus.textContent = status.model.installed ? "READY" : "NOT INSTALLED";
  bar.style.width = "0%";
  install.hidden = false;
  const ready = status.hardware.memoryOkay && status.hardware.diskOkay;
  const missing = status.model.installed ? status.relevance : status.model;
  progressLabel.textContent = ready ? `${missing.label} · ${size(missing.bytes)}` : "This computer needs more memory or space.";
  install.disabled = !status.hardware.memoryOkay || !status.hardware.diskOkay;
}

window.pocketI.onSetupProgress(({ received, total, label }) => {
  const percent = Math.min(100, received / total * 100);
  bar.style.width = `${percent}%`;
  progressLabel.textContent = `Downloading ${label || "local model"} · ${size(received)} / ${size(total)}`;
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
  const before = await window.pocketI.setupStatus();
  if (before.mode === "remote" && before.consentRequired) {
    setupView.hidden = true;
    chatView.hidden = true;
    remoteConsent.hidden = false;
    install.disabled = false;
    return;
  }
  modelStatus.textContent = before.mode === "remote" ? "CONNECTING" : (before.model.installed ? "READY" : "DOWNLOADING");
  rerankerStatus.textContent = before.mode === "remote" ? "CONNECTING" : (before.relevance?.installed ? "READY" : "DOWNLOADING");
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

remoteBrainToggle.addEventListener("click", async () => {
  errorBox.hidden = true;
  if (!remoteConsented) {
    setupView.hidden = true;
    chatView.hidden = true;
    memoryConsent.hidden = true;
    remoteConsent.hidden = false;
    return;
  }
  try {
    await window.pocketI.setRemoteBrain(false);
    remoteConsent.hidden = true;
    await renderStatus();
  } catch (error) {
    errorBox.textContent = error.message || "Remote brain could not be turned off.";
    errorBox.hidden = false;
  }
});

remoteCancel.addEventListener("click", async () => {
  remoteConsentDismissed = true;
  remoteConsent.hidden = true;
  await renderStatus();
});

remoteConfirm.addEventListener("click", async () => {
  remoteConfirm.disabled = true;
  errorBox.hidden = true;
  try {
    remoteConsentDismissed = false;
    await window.pocketI.setRemoteBrain(true);
    remoteConsent.hidden = true;
    await renderStatus();
  } catch (error) {
    errorBox.textContent = error.message || "Yuka’s server could not be reached.";
    errorBox.hidden = false;
    remoteConsent.hidden = true;
    setupView.hidden = false;
  } finally {
    remoteConfirm.disabled = false;
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
      const result = await window.pocketI.answerMemory(question);
      pending.textContent = result.answer;
      pending.classList.remove("pending");
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
