# Pocket i — start here

Contributor onboarding · 9 September 2026

## What we are trying to build

Pocket i is a personal AI that helps its owner use their accumulated experience,
understand where an answer comes from, and eventually collaborate with other
people through their own Pocket i.

Our larger question is: **can independent personal intelligences, each retaining
its owner's knowledge and individuality, become more useful together?** We want
people to control their intelligence and decide what knowledge they share.
A useful network does not require everyone to surrender their private archive
to one central model. Whether our proposed network actually improves capability
is something to test, not a result we have already established.

Yuka started this project alone and is now inviting collaborators to build it
together. The immediate job is to make a small, reliable product that real
people can use. The larger vision gives that work a direction.

## What exists today

The desktop app searches local Codex and Claude Code conversations, extracts
candidate evidence, checks it against the source, and produces a cited answer.
There is a macOS alpha and a small invited-user pilot.

At this review, `main` points to `cb7a35b` and `desktop/app/package.json` declares
`0.1.0-alpha.35`. That is a source checkpoint, not a claim that every installed
build has been updated or that this revision has passed a new physical test.
Alpha.35 addresses an oversized-chat failure by bounding model inputs in UTF-8
bytes and retaining complete paragraphs when a whole turn cannot fit.

Local components include conversation discovery, the search index, exact-source
checks, DeBERTa verification, secret scanning, and private audit logs. Qwen3-8B
and Qwen3-Reranker-4B currently run on the project's server through an authenticated
HTTPS gateway. Remote inference requires the owner's explicit consent.
**The current default setup is therefore not fully offline.**

The repository also contains older public research flows and neural/network
experiments. Those are valuable evidence and history, but they are not proof
that the desktop app already implements a production network of personal AIs.

## The current answer pipeline

1. Local lexical and semantic search selects likely conversations.
2. The context builder retains whole conversations, turns, or selected whole
   paragraphs within the input budget, preserving source coordinates.
3. The reranker filters candidate contexts.
4. Qwen selects messages and extracts small claims with source handles.
5. Ordinary code resolves those handles to exact source text.
6. Local DeBERTa checks whether the source supports each claim.
7. A secret scanner checks the retained claims; Qwen checks question relevance.
8. DeBERTa groups mutually supporting claims. Qwen produces readable versions,
   which are checked again; alternatives are preserved separately.
9. Qwen writes from the verified evidence bundle, and code validates citations.

Two important limitations: the present secret scan happens after early remote
calls, so it does not protect every outbound input; validating final citation
IDs is not the same as proving every sentence in the final answer. Neither
DeBERTa nor the full harness should be described as an infallible truth engine.

## Why this is also a game

We want the experience of building and owning Pocket i to feel personal and
playful. Early participants receive individual invitations and a match: a small
piece of fire passed from one person to another. The metaphor is Prometheus
sharing fire and people learning to use it together.

The current design direction is a small modular robot. At its first awakening,
the owner brings a lit match to an aperture in a suspended chest reactor. The
reactor lights up and the robot comes alive. Its optics, memory cartridges,
verification tools, and other parts can be changed as the product improves.
Concept sketches and an initial editable Blender model exist in a separate
design workspace; this onboarding does not imply they are integrated or bundled
in this repository. Ask Yuka for those assets before implementing against them.

The robot and missions should express real progress. A better search module
should demonstrate better retrieval on a shared test set. A cosmetic shield
must not disable privacy protections when removed. Participants choose bounded
missions; nobody should be an irreplaceable dependency that blocks everyone else.

A first network milestone would be two owners solving a real question using a
specifically approved evidence exchange, with useful citations and a measurable
benefit. That product milestone remains to be built and validated.

## Where you can help

Pick one track with Yuka, then propose the smallest reproducible improvement.

| Track | First useful contribution | Evidence of improvement |
| --- | --- | --- |
| Retrieval and small models | Reproduce a case where available evidence is lost; locate the loss in search, context selection, or reranking | Better recall on fixed cases without flooding later stages |
| Evidence and harness | Catch an unsupported final statement or a false rejection | Before/after cases, supported citations, and honest refusal behavior |
| Privacy and transport | Inspect actual outbound boundaries and move necessary screening before transmission | Synthetic-secret tests showing blocked data never reaches a mocked endpoint |
| Desktop reliability | Reproduce setup, packaging, input-size, cancellation, or recovery failures | A clean-machine or packaged-app reproduction and verified fix |
| Game and 3D interaction | Prototype the first awakening with replaceable robot modules | A playable sequence and editable assets; no invented backend capabilities |
| Collaboration | Design and test a minimal approved evidence exchange between two owners | One real joint task, explicit sharing boundaries, and comparison with working alone |

Fine-tuning is an option when the diagnosis supports it, not a mandatory first
step. A smaller code or prompt change may solve the problem more directly.

## Repository map and first development session

- `desktop/app/`: Electron main process, renderer, inference orchestration.
- `desktop/pocket_i_app/`: Python sidecar and model bridge.
- `desktop/pocket_i_core/`: library adapters, retrieval, index, core logic.
- `desktop/tests/` and `desktop/app/tests/`: regression tests.
- `site/experiments/E007/`: versioned build helpers and public experiment records.
- `experiments/`: research implementations and records; read each experiment's scope.
- `site/` and `server/`: public laboratory website and supporting services.
- `GAME.md`, `METHOD.md`, `DATA.md`: research/game contracts and evidence conventions.
- `PRIVACY.md`, `SECURITY.md`, `ETHICS.md`: data and contribution boundaries.

Start from current `main`. Older branches, including `agent/game-loop-v0.1`,
contain useful history but are not automatically the latest desktop code.
Coordinate any work already in progress before choosing a base.

```sh
git clone https://github.com/yukakust/joinmultiplayer.ai.git
cd joinmultiplayer.ai
git switch -c your-name/short-change-description
PYTHONPATH=desktop python3 -m unittest discover -s desktop/tests -p 'test_*.py'
npm --prefix desktop/app test
```

These commands run the core/desktop test suites; they do not install model
weights or prove the packaged app works. For the Electron development shell:

```sh
npm --prefix desktop/app ci
npm --prefix desktop/app start
```

Full use requires the sidecar/runtime resources and inference configuration.
See `desktop/README.md` for build history and `desktop/app/build-current-platform.sh`
for packaging. Coordinate server access and a current build with Yuka privately;
repository access does not grant production or inference credentials. Do not
run historical deployment commands as part of onboarding.

Open a pull request with the problem, change, validation, and remaining limits.
Agree with Yuka before merging or deploying. Prefer simple, inspectable changes;
borrow useful patterns from nature when they actually simplify the system.

## Data that must stay private

Never commit or publish private chats, questions, excerpts, local paths,
participant identifiers, invitation tokens, credentials, or raw audit logs.
Use synthetic fixtures or explicitly approved, sanitized examples. Keep failed
public experiments and corrections: they are part of the research record.
Repository write access is for collaboration, not permission to publish private
user data or change production access.

## Business hypothesis — not a shipped feature

We are discussing relevant sponsored offers alongside answers. A commercial
Pocket i could provide offers while the owner's Pocket i selects what is useful.
The proposed boundary is that sponsorship cannot buy influence over evidence
or the answer; offers must be identifiable as advertising, and matching should
minimize data leaving the device. There is no validated advertising business,
implemented ad network, or revenue promise yet.

## What success looks like next

An invited person installs Pocket i, gets a useful answer from their own
experience with inspectable sources, and can report or fix one concrete failure.
Then we test one useful, approved exchange between two owners. The game should
make those moments memorable; the engineering must make them real.
