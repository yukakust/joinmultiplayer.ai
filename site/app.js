const repository = "https://github.com/yukakust/joinmultiplayer.ai";
const contribution = `${repository}/issues/new?template=observation.yml`;

const doors = {
  d01: {
    card: "THE WORLD CHANGED.\nTHE MODEL DIDN'T.\n\nCAN IT KNOW?",
    copy: "Find one fact that changed. Ask an AI without warning it. Bring the complete answer and a dated source."
  },
  d02: {
    card: "AI WAS SINGLE-PLAYER.\n\nWHAT IF\nINTELLIGENCE\nIS MULTIPLAYER?",
    copy: "Compare one frontier model with a team of small intelligences under the same declared resource budget."
  },
  d03: {
    card: "WHERE DOES AN AI\nSTOP KNOWING\n\nAND START\nGUESSING?",
    copy: "Build a ladder of questions in a field you know. Record where accuracy breaks—and whether confidence breaks with it."
  },
  d04: {
    card: "IF EVERY AI AGREES,\n\nCAN THEY ALL\nBE WRONG?",
    copy: "Ask at least three AI systems the exact same question independently. Bring every raw answer and an independent verification."
  },
  d05: {
    card: "CAN YOU TRACE\nA ‘FACT’ AI REPEATS\n\nBACK TO ITS\nFIRST SOURCE?",
    copy: "Join Claim Hunt 001. Follow a repeated claim backward until you reach primary evidence—or document where the trail goes cold."
  },
  d06: {
    card: "AI THINKS\nIT KNOWS\nYOUR JOB.\n\nWHAT'S ONE MISTAKE\nONLY AN EXPERT\nWOULD CATCH?",
    copy: "Bring one checkable professional mistake: the exact question, complete answer, correction, and conditions where it applies."
  },
  d07: {
    card: "AI DOES\nTHE TASK.\n\nWHAT DO\nYOU DO?",
    copy: "Name one thing you still define, notice, decide, or remain responsible for when AI produces the output."
  },
  d08: {
    card: "WHEN AIs DISAGREE,\n\nWHICH ANSWER\nDO YOU TRUST?",
    copy: "Blind Judge 001 will open when D04 produces its first real disagreement.",
    waiting: true,
    next: "/d04"
  },
  d09: {
    card: "YOU KNOW IT.\n\nDO YOU KNOW\nWHERE YOU\nLEARNED IT?",
    copy: "Source Memory 001 will open when Claim Hunt finds a real claim that people already recognize.",
    waiting: true,
    next: "/d05"
  },
  d10: {
    card: "TWO HEADS\nARE BETTER THAN ONE.\n\nTOO MANY COOKS\nSPOIL THE BROTH.\n\nWHICH ONE\nIS TRUE FOR AI?",
    copy: "Help test whether a network gains value from each new person's knowledge—or mostly rediscovers what it already knows."
  }
};

function home() {
  return `
    <section class="home">
      <div class="mark" aria-label="i">i</div>
      <h1>Can many small intelligences become smarter than one big AI?</h1>
      <p>We don't know.<br>Let's find out.</p>
      <div class="links">
        <a class="button" href="/d04">Enter</a>
        <a class="quiet-link" href="${repository}">open laboratory</a>
      </div>
    </section>`;
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

const path = window.location.pathname.replace(/^\/+|\/+$/g, "").toLowerCase();
const app = document.querySelector("#app");

if (!path) {
  app.innerHTML = home();
} else if (doors[path]) {
  document.title = `${path.toUpperCase()} — i`;
  app.innerHTML = door(path, doors[path]);
} else {
  app.innerHTML = notFound();
}
