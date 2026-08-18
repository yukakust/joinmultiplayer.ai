const repository = "https://github.com/yukakust/joinmultiplayer.ai";
const contribution = `${repository}/issues/new?template=observation.yml`;
const storageKey = "multiplayer-d04-prototype-v1";

const doors = {
  d01: {
    card: "THE WORLD CHANGED.\nTHE MODEL DIDN'T.\n\nCAN IT KNOW?",
    short: "Can an AI notice that its knowledge expired?",
    copy: "Bring one fact that changed and the complete answer an AI gave without warning."
  },
  d02: {
    card: "AI WAS SINGLE-PLAYER.\n\nWHAT IF\nINTELLIGENCE\nIS MULTIPLAYER?",
    short: "Can many small intelligences beat one frontier model?",
    copy: "Compare one frontier model with a team of small intelligences under the same declared resource budget."
  },
  d03: {
    card: "WHERE DOES AN AI\nSTOP KNOWING\n\nAND START\nGUESSING?",
    short: "Where does an AI stop knowing and start guessing?",
    copy: "Build a ladder of questions in a field you know and find where accuracy breaks."
  },
  d04: {
    card: "IF EVERY AI AGREES,\n\nCAN THEY ALL\nBE WRONG?",
    short: "Can several AIs share the same blind spot?",
    copy: "Bring a question you genuinely wanted answered. Ask several AIs exactly the same way. Bring every answer."
  },
  d05: {
    card: "CAN YOU TRACE\nA ‘FACT’ AI REPEATS\n\nBACK TO ITS\nFIRST SOURCE?",
    short: "Can you trace an AI fact to its first source?",
    copy: "Follow a repeated claim backward until you reach primary evidence—or document where the trail goes cold."
  },
  d06: {
    card: "AI THINKS\nIT KNOWS\nYOUR JOB.\n\nWHAT'S ONE MISTAKE\nONLY AN EXPERT\nWOULD CATCH?",
    short: "What mistake would only a practitioner catch?",
    copy: "Bring one checkable professional mistake and the conditions where it applies."
  },
  d07: {
    card: "AI DOES\nTHE TASK.\n\nWHAT DO\nYOU DO?",
    short: "When AI does the task, what do you still do?",
    copy: "Name one thing you still define, notice, decide, or remain responsible for."
  },
  d08: {
    card: "WHEN AIs DISAGREE,\n\nWHICH ANSWER\nDO YOU TRUST?",
    short: "When AIs disagree, which answer do you trust?",
    copy: "Blind Judge 001 opens only when D04 produces a real disagreement.",
    waiting: true,
    next: "/d04"
  },
  d09: {
    card: "YOU KNOW IT.\n\nDO YOU KNOW\nWHERE YOU\nLEARNED IT?",
    short: "Do you know where a familiar fact entered your memory?",
    copy: "Source Memory 001 opens only when Claim Hunt finds a real familiar claim.",
    waiting: true,
    next: "/d05"
  },
  d10: {
    card: "TWO HEADS\nARE BETTER THAN ONE.\n\nTOO MANY COOKS\nSPOIL THE BROTH.\n\nWHICH ONE\nIS TRUE FOR AI?",
    short: "Which old rule is true for AI?",
    copy: "Test whether another intelligence adds missing knowledge or only more coordination cost."
  }
};

const openDoors = ["d01", "d02", "d03", "d04", "d05", "d06", "d07", "d10"];
const hand = ["d04", "d06", "d10"];
let activeDoorIndex = null;

function defaultPrototype() {
  return {
    stage: "intro",
    question: null,
    responses: [],
    trace: null,
    profile: null,
    verification: null
  };
}

function loadPrototype() {
  try {
    return { ...defaultPrototype(), ...JSON.parse(localStorage.getItem(storageKey) || "{}") };
  } catch {
    return defaultPrototype();
  }
}

let prototype = loadPrototype();

function savePrototype() {
  localStorage.setItem(storageKey, JSON.stringify(prototype));
}

function escapeHTML(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function localId(prefix) {
  return `${prefix}${String(Date.now()).slice(-4)}`;
}

async function copyText(value, button) {
  try {
    await navigator.clipboard.writeText(value);
    const previous = button.textContent;
    button.textContent = "Copied";
    setTimeout(() => { button.textContent = previous; }, 1200);
  } catch {
    window.prompt("Copy this:", value);
  }
}

function home() {
  return `
    <section class="home">
      <div class="mark" aria-label="i">i</div>
      <h1>
        <span>Can people and their pocket AIs</span>
        <span>become smarter together than</span>
        <span>one big AI?</span>
      </h1>
      <p>We don't know.<br>Let's find out together.</p>
      <div class="links">
        <a class="button" href="#hand">Enter</a>
        <a class="quiet-link" href="${repository}">open laboratory</a>
      </div>
    </section>
    <section class="hand-section" id="hand">
      <div class="equation-stage" id="equation-stage" aria-live="polite"></div>
      <div class="catalog-peek">
        <button class="text-button" data-action="show-all">see all open questions</button>
        <div class="all-doors" id="all-doors" hidden></div>
      </div>
    </section>`;
}

function revealedDoor(id) {
  const data = doors[id];
  return `
    <article class="lit-door">
      <div class="lit-symbol" aria-hidden="true">i</div>
      <div class="door-id">i · ${id.toUpperCase()}</div>
      <div class="lit-hook">${escapeHTML(data.card)}</div>
      <p>${escapeHTML(data.copy)}</p>
      <div class="actions">
        <a class="button" href="/${id}">${id === "d04" ? "Try it" : "Enter this door"}</a>
        <button class="text-button" data-action="close-door">another i</button>
      </div>
    </article>`;
}

function renderHand() {
  const target = document.querySelector("#equation-stage");
  if (!target) return;
  if (activeDoorIndex !== null) {
    target.innerHTML = revealedDoor(hand[activeDoorIndex]);
    return;
  }

  target.innerHTML = `
    <div class="equation-wrap">
      <div class="equation" aria-label="Three intelligences lead to an unknown">
        ${hand.map((id, index) => `
          ${index ? "<b>+</b>" : ""}
          <button class="equation-i" data-reveal="${index}" aria-label="Touch an i to reveal a question">i</button>
        `).join("")}
        <b>→</b><span class="equation-unknown">?</span>
      </div>
      <p class="touch-hint">touch an i</p>
    </div>`;
}

function renderAllDoors() {
  const target = document.querySelector("#all-doors");
  if (!target) return;
  target.innerHTML = `
    <div class="door-list">
      ${openDoors.map((id) => `
        <a class="door-choice" href="/${id}">
          <span class="door-choice-id">${id.toUpperCase()}</span>
          <span>${escapeHTML(doors[id].short)}</span>
          <span aria-hidden="true">→</span>
        </a>`).join("")}
    </div>`;
}

function prototypeBanner() {
  return `
    <aside class="prototype-banner">
      <span>UX PROTOTYPE</span>
      <span>saved only in this browser · nothing is published · no email is sent</span>
      <button data-action="reset-prototype">reset</button>
    </aside>`;
}

function d04Intro() {
  return `
    <section class="door flow-shell">
      <div class="door-id">i · D04</div>
      <div class="card">${doors.d04.card}</div>
      <p class="door-copy">${doors.d04.copy}</p>
      <p class="principle">The door gives you a method.<br>You bring the question.</p>
      <div class="actions">
        <button class="button" data-action="start-question">Bring my question</button>
        <a class="button secondary" href="/">Return to i</a>
      </div>
    </section>`;
}

function questionForm() {
  return `
    <section class="flow-shell form-page">
      <div class="flow-step">D04 · QUESTION</div>
      <h1>What do you<br>want to know?</h1>
      <form data-form="question" class="research-form">
        <label>
          Your exact question
          <textarea name="question" rows="4" required placeholder="Write it exactly as you will ask every AI."></textarea>
        </label>
        <label>
          Why does it matter to you?
          <textarea name="why" rows="3" required></textarea>
        </label>
        <label>
          Field or domain
          <input name="domain" required placeholder="e.g. architecture, tax law, beekeeping">
        </label>
        <div class="form-grid">
          <label>
            Do you know the answer?
            <select name="knowledge" required>
              <option value="">Choose</option>
              <option value="know">I know</option>
              <option value="partly know">I partly know</option>
              <option value="do not know">I don't know</option>
            </select>
          </label>
          <label>
            How could it be checked?
            <select name="checkPath" required>
              <option value="">Choose</option>
              <option value="source">A source</option>
              <option value="reproduction">Reproduce it</option>
              <option value="expert review">Expert review</option>
              <option value="unknown">I don't know yet</option>
            </select>
          </label>
        </div>
        <details>
          <summary>I have an expected answer</summary>
          <label>
            Seal it before seeing the AI answers
            <textarea name="expected" rows="3" placeholder="This stays hidden in the verifier view."></textarea>
          </label>
        </details>
        <button class="button" type="submit">Freeze this question</button>
      </form>
    </section>`;
}

function responseCard(response, index) {
  return `
    <details class="response-record">
      <summary><span>ANSWER ${index + 1}</span><span>${escapeHTML(response.model)}</span></summary>
      <p>${escapeHTML(response.raw)}</p>
      <small>${escapeHTML(response.date)} · ${escapeHTML(response.tools)} · version ${escapeHTML(response.version || "unknown")}</small>
    </details>`;
}

function responsesPage() {
  const count = prototype.responses.length;
  const ready = count >= 3;
  return `
    <section class="flow-shell form-page responses-page">
      <div class="flow-step">${escapeHTML(prototype.question.id)} · TRACE</div>
      <div class="frozen-question">
        <span>FROZEN QUESTION</span>
        <blockquote>${escapeHTML(prototype.question.text)}</blockquote>
        <button class="text-button" data-copy="question">copy question</button>
      </div>
      <div class="answer-progress" aria-label="${count} of 3 answers brought">
        ${[0, 1, 2].map((index) => `<i class="${count > index ? "filled" : ""}">i</i>`).join("<b>+</b>")}
      </div>
      <p class="progress-copy">${count === 0 ? "Bring every answer. Don't select the best one." : count < 3 ? `${count} brought · ${3 - count} before the D04 comparison is ready` : `${count} answers · comparison ready`}</p>
      <div class="response-list">${prototype.responses.map(responseCard).join("")}</div>
      <form data-form="response" class="research-form compact-form">
        <h2>Bring ${count === 0 ? "the first" : "another"} answer</h2>
        <div class="form-grid">
          <label>
            AI / model
            <input name="model" required placeholder="e.g. Claude Opus 4.1">
          </label>
          <label>
            Version
            <input name="version" placeholder="exact, dated, or unknown">
          </label>
          <label>
            Date
            <input type="date" name="date" value="${today()}" required>
          </label>
          <label>
            Tools available
            <select name="tools" required>
              <option value="none">None</option>
              <option value="browsing">Browsing</option>
              <option value="files">Files</option>
              <option value="code">Code</option>
              <option value="memory">Memory</option>
              <option value="unknown">Unknown</option>
            </select>
          </label>
        </div>
        <label>
          Complete, unedited answer
          <textarea name="raw" rows="7" required></textarea>
        </label>
        <button class="button secondary" type="submit">Add this answer</button>
      </form>
      ${ready ? `
        <form data-form="seal" class="seal-form">
          <label>
            What happened between the answers?
            <select name="pattern" required>
              <option value="">Choose only after bringing them all</option>
              <option value="agreement">They agree</option>
              <option value="disagreement">They disagree</option>
              <option value="partial disagreement">They partly disagree</option>
              <option value="unclear">I cannot tell</option>
            </select>
          </label>
          <button class="button" type="submit">Seal this trace</button>
          <p>Raw answers stay unchanged. Corrections may be added, never hidden.</p>
        </form>` : ""}
    </section>`;
}

function identityPage() {
  return `
    <section class="flow-shell form-page identity-page">
      <div class="flow-step">${escapeHTML(prototype.trace.id)} · IDENTITY</div>
      <h1>Your trace exists.</h1>
      <p>Who left it?</p>
      <form data-form="identity" class="research-form">
        <label>
          Public name or pseudonym
          <input name="name" placeholder="Leave blank to appear as anonymous">
        </label>
        <div class="form-grid">
          <label>
            Image or symbol
            <input name="symbol" maxlength="3" placeholder="i">
          </label>
          <label>
            Approximate location
            <input name="location" placeholder="optional · never exact">
          </label>
        </div>
        <label>
          Email for status updates
          <input type="email" name="email" placeholder="optional · prototype only">
          <small>No email is sent in this prototype.</small>
        </label>
        <label class="check-label">
          <input type="checkbox" name="mapConsent">
          Show this identity on the future public ignition map
        </label>
        <button class="button" type="submit">Enter as ı</button>
      </form>
    </section>`;
}

function mapMarkup(final = false) {
  const profile = prototype.profile || { name: "anonymous", symbol: "ı", matchId: "M0002" };
  return `
    <div class="map-canvas ${final ? "map-final" : ""}" aria-label="Ignition map prototype">
      <div class="map-line origin-line"></div>
      ${final ? `<div class="map-line dotted-line"></div>` : ""}
      <div class="map-node origin-node"><b>i</b><span>M0001<br>origin</span></div>
      <div class="map-node player-node"><b>${final ? "i" : "ı"}</b><span>${escapeHTML(profile.matchId)}<br>${escapeHTML(profile.name || "anonymous")}</span></div>
      ${final ? `<div class="map-node verifier-node"><b>ı</b><span>M0003<br>verifier</span></div>` : ""}
    </div>`;
}

function statusPage() {
  const statusUrl = `${location.origin}/d04/#status-${prototype.profile.statusToken}`;
  return `
    <section class="flow-shell status-page">
      <div class="flow-step">${escapeHTML(prototype.profile.matchId)} · AWAITING ANOTHER i</div>
      <div class="large-state">ı</div>
      <h1>Your trace exists.<br>It does not have a dot yet.</h1>
      ${mapMarkup(false)}
      <div class="record-summary">
        <span>${escapeHTML(prototype.question.id)}</span>
        <span>${escapeHTML(prototype.trace.id)}</span>
        <span>${prototype.responses.length} AI answers</span>
        <span>${escapeHTML(prototype.trace.pattern)}</span>
      </div>
      <div class="status-link">
        <span>PRIVATE STATUS LINK</span>
        <code>${escapeHTML(statusUrl)}</code>
        <button class="text-button" data-copy="status">copy link</button>
      </div>
      <div class="next-actions">
        <button class="button" data-action="invite">Invite an i to check it</button>
        <button class="button secondary" data-action="ask-network">Ask the network</button>
        <button class="text-button" data-action="open-verifier">switch to verifier view →</button>
      </div>
      <p class="prototype-note">The verifier switch exists only so you can walk through both sides of the prototype.</p>
    </section>`;
}

function verifierPage() {
  return `
    <section class="flow-shell form-page verifier-page">
      <div class="flow-step">ANOTHER i · INDEPENDENT CHECK</div>
      <h1>Can you check<br>this trace?</h1>
      <div class="blind-record">
        <span>QUESTION</span>
        <blockquote>${escapeHTML(prototype.question.text)}</blockquote>
        <span>RAW ANSWERS</span>
        ${prototype.responses.map(responseCard).join("")}
        <p>The creator's expected answer and interpretation are hidden.</p>
      </div>
      <form data-form="verification" class="research-form">
        <label>
          What did you check?
          <select name="scope" required>
            <option value="">Choose</option>
            <option value="ground truth">Ground truth</option>
            <option value="reproduction">Reproduction</option>
            <option value="expert review">Expert review</option>
          </select>
        </label>
        <label>
          How did you check it?
          <textarea name="method" rows="4" required></textarea>
        </label>
        <label>
          Evidence or direct sources
          <textarea name="evidence" rows="4" required></textarea>
        </label>
        <label>
          Outcome
          <select name="outcome" required>
            <option value="">Choose</option>
            <option value="supports">Supports</option>
            <option value="challenges">Challenges</option>
            <option value="inconclusive">Inconclusive</option>
          </select>
        </label>
        <label>
          Limitations
          <textarea name="limitations" rows="3" required></textarea>
        </label>
        <label class="check-label">
          <input type="checkbox" name="independent" required>
          I did not create this trace or see its sealed interpretation
        </label>
        <button class="button" type="submit">Publish this check</button>
      </form>
    </section>`;
}

function finalPage() {
  const openedDoor = prototype.trace.pattern.includes("disagreement");
  return `
    <section class="flow-shell final-page">
      <div class="flow-step">${escapeHTML(prototype.profile.matchId)} · DOTTED BY M0003</div>
      <div class="large-state">i</div>
      <h1>Another i<br>checked your trace.</h1>
      <p class="outcome">Outcome: <strong>${escapeHTML(prototype.verification.outcome)}</strong></p>
      ${mapMarkup(true)}
      <div class="notification-preview">
        <span>EMAIL PREVIEW</span>
        <h2>Another i put a dot on your trace.</h2>
        <p>${escapeHTML(prototype.trace.id)} was independently checked. Outcome: ${escapeHTML(prototype.verification.outcome)}.</p>
      </div>
      ${openedDoor ? `
        <div class="door-unlocked">
          <span>YOU OPENED A NEW DOOR</span>
          <h2>D08 · Blind Judge 001</h2>
          <p>The models disagreed. Can people recognize the correct answer?</p>
        </div>` : `
        <div class="door-unlocked">
          <span>THE LAB CHANGED</span>
          <h2>Agreement survived one check.</h2>
          <p>One case is not the answer. The trace is now ready to be repeated.</p>
        </div>`}
      <div class="actions">
        <button class="button" data-action="reset-prototype">Start another trace</button>
        <a class="button secondary" href="/">Return to i</a>
      </div>
    </section>`;
}

function d04Flow() {
  const screens = {
    intro: d04Intro,
    question: questionForm,
    responses: responsesPage,
    identity: identityPage,
    status: statusPage,
    verifier: verifierPage,
    final: finalPage
  };
  const screen = screens[prototype.stage] || d04Intro;
  return `${prototypeBanner()}${screen()}`;
}

function door(id, data) {
  const action = data.waiting
    ? `<p class="status">Waiting for a real case. Nothing fictional will be placed here.</p>
       <a class="button" href="${data.next}">Open the source door</a>`
    : `<a class="button" href="${contribution}&title=%5B${id.toUpperCase()}%5D%20">Bring an observation</a>`;

  return `
    <section class="door">
      <div class="door-id">i · ${id.toUpperCase()}</div>
      <div class="card">${data.card}</div>
      <p class="door-copy">${data.copy}</p>
      <div class="actions">
        ${action}
        <a class="button secondary" href="/">Return to i</a>
      </div>
    </section>`;
}

function notFound() {
  document.title = "Not found — i";
  return `
    <section class="not-found">
      <div class="door-id">404</div>
      <h1>No door here yet.</h1>
      <a class="button" href="/">Return to i</a>
    </section>`;
}

function render() {
  const path = window.location.pathname.replace(/^\/+|\/+$/g, "").toLowerCase();
  if (!path) {
    document.title = "i — multiplayer intelligence";
    app.innerHTML = home();
    renderHand();
    renderAllDoors();
  } else if (path === "d04") {
    document.title = "D04 — i";
    app.innerHTML = d04Flow();
  } else if (doors[path]) {
    document.title = `${path.toUpperCase()} — i`;
    app.innerHTML = door(path, doors[path]);
  } else {
    app.innerHTML = notFound();
  }
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

const app = document.querySelector("#app");

app.addEventListener("click", (event) => {
  const revealButton = event.target.closest("[data-reveal]");
  if (revealButton) {
    activeDoorIndex = Number(revealButton.dataset.reveal);
    renderHand();
    document.querySelector(".lit-door .button")?.focus();
    return;
  }

  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action === "show-all") {
    const list = document.querySelector("#all-doors");
    list.hidden = !list.hidden;
    event.target.textContent = list.hidden ? "see all open questions" : "hide open questions";
  }
  if (action === "close-door") {
    activeDoorIndex = null;
    renderHand();
    document.querySelector(".equation-i")?.focus();
  }
  if (action === "start-question") {
    prototype.stage = "question";
    savePrototype();
    render();
    scrollTo(0, 0);
  }
  if (action === "reset-prototype") {
    if (confirm("Clear this browser-only prototype trace?")) {
      prototype = defaultPrototype();
      savePrototype();
      render();
      scrollTo(0, 0);
    }
  }
  if (action === "invite") {
    const value = `${location.origin}/d04/?lit=${prototype.profile.matchId}`;
    copyText(value, event.target);
  }
  if (action === "ask-network") {
    event.target.textContent = "Added to the prototype queue";
    event.target.disabled = true;
  }
  if (action === "open-verifier") {
    prototype.stage = "verifier";
    savePrototype();
    render();
    scrollTo(0, 0);
  }

  const copyButton = event.target.closest("[data-copy]");
  if (copyButton?.dataset.copy === "question") copyText(prototype.question.text, copyButton);
  if (copyButton?.dataset.copy === "status") {
    copyText(`${location.origin}/d04/#status-${prototype.profile.statusToken}`, copyButton);
  }
});

app.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.target;
  const data = formData(form);

  if (form.dataset.form === "question") {
    prototype.question = {
      id: localId("Q"),
      text: data.question.trim(),
      why: data.why.trim(),
      domain: data.domain.trim(),
      knowledge: data.knowledge,
      checkPath: data.checkPath,
      expected: data.expected.trim()
    };
    prototype.stage = "responses";
  }

  if (form.dataset.form === "response") {
    prototype.responses.push({
      model: data.model.trim(),
      version: data.version.trim() || "unknown",
      date: data.date,
      tools: data.tools,
      raw: data.raw.trim()
    });
  }

  if (form.dataset.form === "seal") {
    prototype.trace = {
      id: localId("T"),
      pattern: data.pattern,
      sealedAt: new Date().toISOString()
    };
    prototype.stage = "identity";
  }

  if (form.dataset.form === "identity") {
    prototype.profile = {
      matchId: "M0002",
      name: data.name.trim() || "anonymous",
      symbol: data.symbol.trim() || "ı",
      location: data.location.trim(),
      email: data.email.trim(),
      mapConsent: data.mapConsent === "on",
      statusToken: crypto.randomUUID().slice(0, 12)
    };
    prototype.stage = "status";
  }

  if (form.dataset.form === "verification") {
    prototype.verification = {
      id: localId("V"),
      scope: data.scope,
      method: data.method.trim(),
      evidence: data.evidence.trim(),
      outcome: data.outcome,
      limitations: data.limitations.trim()
    };
    prototype.stage = "final";
  }

  savePrototype();
  render();
  scrollTo(0, 0);
});

render();
