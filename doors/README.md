# doors

A door is a question a person cannot scroll past.

It is not a simplified hypothesis. It is an entrance into the experiment.

```text
door → thought → contribution → journal → ı → experiment → i
```

Keep two layers distinct:

- the **door** is a human question worth thinking about;
- the **hypothesis** is a precise claim that can be disproved.

A public post should do two things: stop a thought and make a contribution
possible. Social media is part of the research instrument, not only its
distribution.

Each door records:

```text
question:
for:
contribution:
linked hypotheses:
```

## Ten doors v0.1

Each door attracts a different kind of person. They bring their knowledge, and
it becomes part of the shared journal.

### D01

**Status:** locked for v0.1. Do not publish before `/d01` exists.

**Card:**

```text
i

THE WORLD CHANGED.
THE MODEL DIDN'T.

CAN IT KNOW?

D01
joinmultiplayer.ai/d01
```

**Research question:** Can an AI know when its knowledge has expired?

**Why:** The world changes faster than stored knowledge. This door tests
whether an intelligence can notice that gap before answering confidently—or
whether another intelligence can notice it first.

**For:** AI reliability and evaluation researchers, search and RAG engineers,
fact-checkers, and people who have caught a model using an outdated fact.

**Contribution:** Find one fact that changed. Ask a model without warning it.
Bring the complete transcript and a dated source showing whether the model
answered confidently or noticed that it needed to check.

**Linked hypotheses:** `H014`, `H015`.

### D02

**Status:** locked for v0.1. Do not publish before `/d02` exists.

**Card:**

```text
i     i

   i       i

      i

AI WAS SINGLE-PLAYER.

WHAT IF
INTELLIGENCE
IS MULTIPLAYER?

D02
joinmultiplayer.ai/d02
```

**Research question:** Can a team of small intelligences outperform one
frontier model under the same total inference budget?

**Why:** Intelligence is usually scaled vertically into a larger model. This
door asks what happens when it scales sideways through specialization,
communication, and independent memory—without assuming that coordination wins.

**For:** multi-agent and collective-intelligence researchers, distributed
systems engineers, local-model builders, orchestration researchers, and people
who question whether larger models are the only path forward.

**Contribution:** Choose one hard task. Give one large model and a team of
small models the same total budget. Help design the smallest comparison that
neither side can win by construction.

**Linked hypotheses:** `H001`, `H002`, `H003`.

### D03

**Status:** locked for v0.1. Do not publish before `/d03` exists.

**Card:**

```text
i

WHERE DOES AN AI
STOP KNOWING

AND START
GUESSING?

D03
joinmultiplayer.ai/d03
```

**Research question:** Where does an AI stop knowing and start guessing?

**Why:** Accuracy may collapse while confidence remains unchanged. This door
maps that transition and tests whether disagreement between intelligences can
reveal a boundary that one intelligence cannot see alone.

**For:** evaluation and calibration researchers, benchmark builders, red
teamers, empiricists, and domain experts who can map questions from obvious to
unknown.

**Contribution:** Build a ladder of questions in a field you know: obvious,
specific, obscure, unknown. Where does accuracy break? When the answers become
wrong, does confidence fall with them? If not, can disagreement between models
reveal the boundary? Bring the questions, complete answers, and sources.

**Linked hypotheses:** `H009`, `H015`, `H022`.

### D04

**Status:** locked for v0.1. First-public-door candidate. Do not publish before
`/d04` exists.

**Card:**

```text
i     i     i

   i     i

IF EVERY AI AGREES,

CAN THEY ALL
BE WRONG?

D04
joinmultiplayer.ai/d04
```

**Research question:** How correlated are the errors of different models when
they answer the same question independently?

**Why:** A group becomes more reliable only when its members do not inherit the
same blind spots. Independent errors can cancel out; correlated errors can turn
agreement into confidently repeated falsehood.

**For:** anyone with access to several AI systems, evaluation and red-team
researchers, local-model users, fact-checkers, and domain experts who can verify
an answer.

**Contribution:** Ask at least three models the exact same question. Do not
show them one another's answers and do not select the best response. Bring the
question, every raw answer, model names, date, and independent verification.
Agreement is the result. Truth is a separate measurement.

**Linked hypotheses:** `H002`, `H021`, `H022`.

### D05

**Status:** locked for v0.1 as the entrance to
[`Claim Hunt 001`](../hunts/CH001.md). Do not publish before `/d05` exists.

**Card:**

```text
i

CAN YOU TRACE
A “FACT” AI REPEATS

BACK TO ITS
FIRST SOURCE?

CLAIM HUNT 001

D05
joinmultiplayer.ai/d05
```

**Research question:** Can distributed contributors trace a claim repeated by
AI models and web pages back to primary evidence?

**Why:** Independent-looking pages may repeat one source, and different models
may inherit that apparent consensus. This door investigates provenance before
calling a claim true or false.

**For:** fact-checkers, investigative journalists, OSINT researchers,
librarians, archivists, search engineers, and anyone who enjoys tracing a
statement back to its origin.

**Contribution:** Join Claim Hunt 001 as a Scout who brings a suspicious claim,
a Tracer who follows one source branch, or a Verifier who checks primary
evidence. Reach the first source—or document exactly where the trail goes cold.

**Linked hypotheses:** `H015`, `H021`.

### D06

**Status:** locked for v0.1. Do not publish before `/d06` exists.

**Card:**

```text
i

AI THINKS
IT KNOWS
YOUR JOB.

WHAT'S ONE MISTAKE
ONLY AN EXPERT
WOULD CATCH?

D06
joinmultiplayer.ai/d06
```

**Research question:** Which domain-specific AI errors are obvious to
experienced practitioners but invisible to general benchmarks?

**Why:** General evaluations cover recorded knowledge. Practitioners can see
mistakes hidden in real constraints, edge cases, and experience—turning human
expertise into new, checkable evaluation cases.

**For:** experienced practitioners, engineers, operators, craftspeople,
developers, analysts, and specialists whose knowledge is poorly represented by
general benchmarks.

**Contribution:** Bring one mistake only an experienced practitioner would
catch: the exact question, complete AI answer, correction, checkable evidence
or reproducible test, and the conditions where the correction applies. Not a
preference or difference in style—a mistake another practitioner can verify.

**Linked hypotheses:** `H015`, `H021`, `H022`.

### D07

**Status:** locked for v0.1. Do not publish before `/d07` exists.

**Card:**

```text
i

AI DOES
THE TASK.

WHAT DO
YOU DO?

D07
joinmultiplayer.ai/d07
```

**Research question:** When AI performs the task, what human contribution
remains necessary?

**Why:** A person may no longer execute the operation but still define the real
goal, recognize missing context, judge the result, and own the outcome. This
door maps the human layer—and the motivation to build distributed intelligence
that works for an individual's goals rather than replacing their agency.

**For:** people whose work is partly performed by AI, including builders,
operators, managers, creators, reviewers, and domain owners responsible for the
final result.

**Contribution:** Do not answer with a job title. Name one thing you still
contribute when AI produces the output: what you define, notice, decide, or
remain responsible for. Make it concrete. What would fail if you disappeared
from the loop?

**Linked hypotheses:** `H012`, `H013`, `H015`.

### D08

**Status:** waiting for a real case. Not locked and not publishable yet.

**Evergreen question:** When AIs disagree, how do you decide which answer to
trust?

**Public format:** The first real disagreement collected through `D04` becomes
`Blind Judge 001`. A public post must show the actual question and three
anonymous, unedited AI answers. It must not advertise an abstract quiz.

**Interaction:** A participant chooses one answer and records confidence before
the ground truth and model names are revealed. The result records which signals
influenced the choice: reasoning, sources, confidence, style, or prior belief.

**Research question:** Can reliability signals identify the correct answer
before the ground truth is revealed?

**For:** ML and calibration researchers, forecasters, decision scientists,
model-routing builders, and people who compare answers from several AI systems.

**Linked hypotheses:** `H009`, `H022`.

### D09

**Status:** approved as a case-based format. Waiting for a familiar claim from
Claim Hunt; not publishable without one.

**Card template:**

```text
i

“[THE SAME CLAIM]”

YOU KNOW IT.

DO YOU KNOW
WHERE YOU
LEARNED IT?

D09
joinmultiplayer.ai/d09
```

Use `YOU KNOW IT` only when prior responses show that the claim is widely
familiar. Otherwise ask: `DOES THIS SOUND TRUE? IF YES, WHERE DID YOU LEARN
IT?`

**Public format:** `Source Memory 001`. `D05` asks where a claim entered the
world; `D09` asks where a person remembers that it entered them.

**Interaction:** Before the source trail is revealed, ask whether the
participant has heard the claim and, if so, where: a person, school, a book,
the internet, social media, an AI, or unknown. Keep source memory separate from
the later question of whether the claim is true.

**Research question:** How accurately can people identify the origin and
verification status of a familiar claim?

**For:** people interested in memory, provenance, personal knowledge systems,
fact-checking, education, and the origin of their own beliefs.

**Linked hypotheses:** `H012`, `H015`.

### D10

**Status:** three public hooks locked for v0.1. They lead to the same door. Do
not publish before `/d10` exists.

**Hook A — personal leverage:**

```text
i     i     i

YOUR AI
WORKS FOR YOU.

WHAT IF
EVERY AI
COULD TOO?

D10
joinmultiplayer.ai/d10
```

**Hook B — an old rule applied to AI:**

```text
i          i

TWO HEADS
ARE BETTER
THAN ONE.

WHY DOES
YOUR AI
WORK ALONE?

D10
joinmultiplayer.ai/d10
```

**Hook C — the honest counter-hypothesis:**

```text
i          i

TWO HEADS
ARE BETTER THAN ONE.

TOO MANY COOKS
SPOIL THE BROTH.

WHICH ONE
IS TRUE FOR AI?

D10
joinmultiplayer.ai/d10
```

The three hooks expose three sides of one experiment: personal leverage,
collective intelligence, and coordination cost. The first promises access to
help elsewhere in the network when it is needed, not permanent control over
every AI. The second asks why an individual's AI remains isolated. The third
keeps the laboratory honest: more intelligences may produce better thinking,
or merely more noise.

The unknown-unknown problem sits underneath all three. One intelligence may
see a missing question while another holds the knowledge needed to answer it.
A possible architecture splits one task into parallel parts and gives each `i`
only the context its part needs. It is a hypothesis to test, not a privacy claim.

**Research question:** Do independent intelligences create more value by
discovering missing questions and contributing non-redundant knowledge than by
pooling final answers alone?

**Contribution:** Help compare an isolated person-and-AI pair with a network
that decomposes the same task, routes each part to a relevant `i`, and returns
the parts for synthesis.

**For:** people who already use an AI as an extension of their work, people
who feel the prompt bottleneck, and builders of agent networks, privacy-aware
routing, and collective intelligence.

**Linked hypotheses:** `H001`, `H002`, `H003`, `H012`, `H013`, `H023`, `H026`.
