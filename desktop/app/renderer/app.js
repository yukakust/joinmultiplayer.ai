const button = document.querySelector("#scan");
const conversations = document.querySelector("#conversations");
const messages = document.querySelector("#messages");
const status = document.querySelector("#status");

async function scan() {
  button.disabled = true;
  button.textContent = "CHECKING…";
  status.textContent = "READING";
  try {
    const result = await window.pocketI.scan();
    conversations.textContent = result.total_conversations.toLocaleString("en");
    messages.textContent = result.total_messages.toLocaleString("en");
    status.textContent = result.total_conversations > 0 ? "READY" : "EMPTY";
  } catch (error) {
    status.textContent = "FAILED";
  } finally {
    button.disabled = false;
    button.textContent = "CHECK AGAIN";
  }
}

button.addEventListener("click", scan);

