# i

> Can many small intelligences become smarter than one big AI?

We don't know.

Let's find out together.

`i + i > AI ?`

- **Brand:** `i`
- **Idea:** multiplayer intelligence
- **Address:** [joinmultiplayer.ai](https://joinmultiplayer.ai)

## The goal

**Can many personal pocket i—each preserving its own knowledge and
individuality—temporarily unite into a single distributed neural network and
grow stronger as the swarm scales?**

The long-range comparison is intentionally asymmetric: a swarm may bring more
people, private experience, and total compute than any single company or model.
Equal-budget controls remain useful for measuring coordination cost, but they
are not the main claim.

This repository is the open laboratory around that question. It does not assume
that the answer is yes.

## i

```text
individual
intelligence
information
a person
a match
```

`i` learns locally. `i` owns its memory. `i` can teach another `i`.

## From question to network

```text
lab discovers → protocol emerges → network works → movement spreads
```

The laboratory is the first working layer of the network, not a content feed to
consume indefinitely. Its questions are open tasks, its traces are work already
done, and its verifications are checks another intelligence can repeat. The map
is the shared task-and-evidence ledger that keeps those objects connected.

The currently agreed harness path—from exact question through local search and
evidence capsules to realized value—is recorded in [`schema.md`](schema.md).

In the standalone-question loop, a participant takes a public question into an
AI they already use and keeps the complete result. The deployed v0.1 form opens
answer-type tasks only, so every offered task can return that result as a linked
trace. Other contribution types stay hidden until their return formats ship. The portable
**task-ready record** carries the exact question, context, requested next move,
provenance, and linked work without requiring an account or a project-specific
agent.

A network-capable pocket `i` is a later product stage. This repository does not
currently offer a pocket-AI download or claim that opening a task pack connects
an agent to a live network. E002 now provides a public experiment page and an
inspectable Codex implementation journal; that journal is laboratory plumbing,
not the pocket i itself. The intended transition is explicit:

```text
open questions and evidence
→ portable task packs
→ read-only user-controlled connector
→ local, explicitly taught memory
→ consented network identity and human-approved contributions
→ multiplayer experiments
```

The current build starts the first synthetic swarm experiment at
[`E002`](experiments/E002-synthetic-pocket-i-swarm/README.md). The repository
also contains the installable [`Pocket i Lab`](plugins/pocket-i-lab) Codex
plugin. After explicit per-task consent, Codex lifecycle hooks keep the journal
from the conversation the participant is already using; no second agent process
is started. The public journal exposes redacted user-visible prompts and final
answers plus tool/action status and relative changed filenames. It excludes raw
reasoning, tool arguments/results, commands/output, file contents, environment
data, local absolute paths, session identifiers, credentials, and the private
publication key.

Install the repository marketplace and plugin, then begin a new Codex task:

```text
codex plugin marketplace add yukakust/joinmultiplayer.ai --ref agent/game-loop-v0.1
codex plugin add pocket-i-lab@joinmultiplayer-lab
```

After reviewing and trusting the hook, opt in from that task with
`$pocket-i-lab start E002 as <pseudonym>`. Inactive hooks perform no network
request. `$pocket-i-lab finish` closes the public run.

[`E003`](experiments/E003-first-physical-swarm/README.md) is the first physical
device step. `/network/` creates a private three-slot room; browser nodes let a
phone and Mac train their own tiny local weights, while the downloadable
headless Python node does the same on a server. One answer has 4,096 possible
values and needs all three complete capsule batches. E003 deliberately tests
device wiring and local personalization only, not a language model or H0001.
The unexecuted next-step design selects local DoRA fine-tuning, one public
experiment microscope, and three visible owner checkpoints; see
[`DORA-LANGUAGE-SWARM-PLAN.md`](experiments/E003-first-physical-swarm/DORA-LANGUAGE-SWARM-PLAN.md).

The lab therefore comes first, but it is meant to become the work surface of
the network. Architecture must earn its place through evidence, and each later
capability must preserve local ownership, inspectability, and human control.

## The lab

```text
doors/         questions people enter through
hunts/         optional public investigations
journal/       observations people bring
hypotheses/    ideas before evidence: ı
experiments/   reproducible tests
i/             results that earned their dot
matches/       people and the traces between them
site/          the public entrance
```

A path through the lab may begin anywhere, but evidence moves in one direction:

```text
door → contribution → journal → hypothesis → experiment → result → next question
```

Enter through a [door](doors/), contribute an
[observation](CONTRIBUTING.md), or start with the
[hypothesis pool](hypotheses/POOL.md).

The public entrance reveals only three questions at first. Read
[`GAME.md`](GAME.md) for the research loop, independent dot, action paths, and
ignition map behind that entrance.

Questions, traces, and independent verifications follow the open
[`Data Contract v0.1`](DATA.md).

A question is a first-class record. It may be opened before anyone has answered
it and picked up years later. The current v0.1 form grows a question from an
older public trace; broader event sources remain part of the data contract, not
the deployed form. The current honest action is **Take this question to my
AI**: use the task pack with an AI you already control. It does not imply that a
model or connector was downloaded.

Public traces can be read at [joinmultiplayer.ai/data](https://joinmultiplayer.ai/data/)
or consumed without an account as
[JSON](https://joinmultiplayer.ai/api/public/records.json) and
[JSONL](https://joinmultiplayer.ai/api/public/records.jsonl). Pending, withdrawn,
and private moderation data are never included in these feeds.

Agents that need the whole public task-and-evidence ledger can start with the
unified [corpus JSON](https://joinmultiplayer.ai/api/public/corpus.json), which
combines public questions, traces, and events without private moderation data.
Its machine-readable contract is
[Corpus Schema v0.2](https://joinmultiplayer.ai/data/corpus-schema-v0.2.json).

Every published move also enters the append-only
[event map](https://joinmultiplayer.ai/map/). A new trace may continue any older
public trace; chronology gives the new event its number while a typed link
preserves where the branch began.

## Rules

- Ask one sharp question.
- Use the smallest honest test.
- Compare against a strong, simple baseline.
- Publish the complete record required by [`METHOD.md`](METHOD.md).
- Publish what failed.
- Separate observation from interpretation.
- Let evidence place the dot.
- No one puts the dot on their own `i`.

Inconclusive and failed experiments belong here too. Every result must say
whether it supports, challenges, or leaves the main question unanswered.

An `i` may live in code, on paper, on a sticker, or on a wall.

Open a question. Take it to your AI. Return what happened. Leave an `i`.

## Participate

Start with [`CONTRIBUTING.md`](CONTRIBUTING.md). Contributions are public by
default; read [`ETHICS.md`](ETHICS.md) and [`PRIVACY.md`](PRIVACY.md) before
sharing data.

Code is licensed under MIT. Original documentation and laboratory data use the
terms in [`DATA_LICENSE.md`](DATA_LICENSE.md).
