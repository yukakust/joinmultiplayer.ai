# Handoff — from E003 wiring to the first language-model pocket i

Audience: a new Codex task with the `pocket-i-lab` plugin enabled.  
Owner: Morrow, with human review and explicit approval at every scientific
lock.  
Execution host for the first phase: `yukabox`.  
Status: **design and feasibility task; do not describe it as a result**.

Read alongside:

- [`POCKET-I-SWARM-MAP.md`](POCKET-I-SWARM-MAP.md) — the durable text version
  of the five Miro frames;
- [`PERSONAL-DELTA-LM-ARCHITECTURE.md`](PERSONAL-DELTA-LM-ARCHITECTURE.md) —
  what can be reused and what the experiment must invent and falsify;
- [`DORA-LANGUAGE-SWARM-PLAN.md`](DORA-LANGUAGE-SWARM-PLAN.md) — the selected
  DoRA training method, mandatory human gates, and public UI contract.

## Start the new Codex task

Open a new Codex task in this repository and send these two messages in order:

```text
$pocket-i-lab start E003 as Morrow
```

```text
Read experiments/E003-first-physical-swarm/NEXT-LANGUAGE-MODEL-HANDOFF.md and
experiments/E003-first-physical-swarm/DORA-LANGUAGE-SWARM-PLAN.md in full.
First explain in plain Russian what will be trained, where the base model will
come from, how 6/12/24-layer branches can share one neural ABI, and what would
falsify the idea. Do not download a model, install GPU software, revive N0001,
or start training until I approve that explanation and the proposed model
shortlist. No later gate may advance without my visible approval either.
```

The first command is explicit consent to the plugin's filtered public journal.
The task must repeat the public journal URL before beginning work.

## Why this handoff exists

E001 showed that independently trained, ABI-compatible neural deltas can be
composed in a controlled synthetic world. E002 made synthetic composition and
swarm growth inspectable. E003 moved a toy learned module across three physical
devices.

None of them created a language-model pocket i.

The current E003 node learns a `16 x 16` classifier from an all-zero matrix. Its
reported local accuracy is accuracy on that controlled table, not language
ability. The private room `N0001` is an unpublished wiring rehearsal. Its
`yukabox` process has been stopped. Do not restart it or use its `100%` metric
as evidence for this task.

This task replaces no previous record. The public journal may continue under
E003 because it documents the transition from physical wiring to the next
experiment. Before any locked language-model run, assign a new experiment ID
and write a separate protocol. The likely working name is:

```text
E004 — Elastic Personal Delta Language Model
```

The human owner must approve the final ID and protocol before a result-bearing
run.

## Main hypothesis

> Can many personal pocket i—each preserving its own knowledge and
> individuality—temporarily unite into a single distributed neural network and
> grow stronger as the swarm scales?

This task tests only the next narrow mechanism:

> Can three language-model branches of different depths begin from compatible
> base behavior, learn different information locally in their own weights, and
> return bounded deltas through one frozen neural ABI so that a shared source
> produces a language answer requiring all three?

A positive result would justify moving the branches to the phone, Mac, and
`yukabox`. It would not prove the global swarm hypothesis.

## What counts as a language-model pocket i in this task

A candidate pocket i must have all of the following:

1. A real pretrained autoregressive language-model base, not a lookup table or
   hand-written capsule.
2. Its own locally changed neural weights and an inspectable training history.
3. A local memory boundary controlled by its owner.
4. A frozen, versioned ingress/egress interface shared with other pocket i.
5. A measurable delta relative to a matching unpersonalized base path.
6. A way to abstain when it adds no relevant information.
7. A local before/after evaluation and checkpoint rollback.

For this first study, all three branches may run as separate processes on
`yukabox`. They are synthetic owners on one host, not three physical pocket i.
Physical deployment comes only after the language mechanism passes.

## Where the base model comes from

Do not train a foundation model from scratch in this phase. That would test the
quality of a new pretraining corpus and optimizer rather than the distributed
architecture.

Select one small, openly downloadable pretrained decoder model only after a
documented shortlist. The shortlist must record:

- exact model and immutable revision;
- license and whether modified weights may be distributed;
- tokenizer license and vocabulary;
- parameter count, hidden size, attention layout, and number of blocks;
- whether the architecture can supply a 24-block teacher or a defensible
  equivalent;
- memory required for inference and local training at `bf16`, `int8`, and
  `int4`;
- CPU support and the audited accelerator path on `yukabox`;
- expected disk download and generated checkpoint size;
- availability of reproducible reference code without remote-code execution.

Target scale for the first shortlist: roughly `0.5B–1.5B` parameters. This is
a starting envelope, not a locked requirement. Prefer the smallest model that
still produces recognizably coherent language and permits the mechanism to be
tested on 64 GB unified memory.

Do not select a checkpoint merely because it is popular. Do not set
`trust_remote_code=True`. Pin and record every downloaded artifact hash.

Long term, a successful mechanism should lead to a Pocket Foundation Model
trained from the beginning for elastic depth and personal neural branches. The
open pretrained model in this task is scaffolding for the experiment, not the
final architecture.

## Proposed architecture

All branches share a tokenizer and canonical latent dimension. The source owns
the trusted common path, router, merger, final layers, and language head.

```text
tokens
  |
  v
shared frozen embedding/stem -> h
  |
  +-> trusted canonical base path ---------------------------> z0
  |
  +->  6-layer base reference / personal branch -> raw d6 --+
  +-> 12-layer base reference / personal branch -> raw d12 -+-> frozen ABI
  +-> 24-layer base reference / personal branch -> raw d24 -+   projections
                                                              |
                    bounded deltas + abstain/confidence -------+
                                                              v
                              z = z0 + Merge(d6, d12, d24)
                                                              |
                                                shared final layers
                                                              |
                                                          next token
```

For a branch with depth `d`:

```text
raw_delta_i = PersonalTower_i,d(h, allowed_local_memory)
              - BaseTower_d(h)

delta_i = ClipAndNormalize(FrozenProjection_d(raw_delta_i), norm_budget)

result = FinalLayers(z0 + Merge(delta_6, delta_12, delta_24, metadata))
```

The personal tower and its matching base reference must start functionally
identical. Therefore a fresh branch should have `raw_delta ~= 0`; zero must be
verified numerically rather than assumed.

### Why 6, 12, and 24 layers can be compatible

Different depths cannot be made compatible by casually deleting layers from a
random checkpoint. Build an elastic family deliberately:

- derive all depths from one pinned teacher lineage;
- keep tokenizer, hidden width, normalization convention, and ABI endpoint
  fixed;
- train or distill the `6`- and `12`-layer paths to preserve the canonical
  interface expected from the `24`-layer teacher;
- use depth sampling/layer dropping during compatibility training;
- give each depth its own frozen projection into the same ABI space;
- freeze the ingress, egress, norm budget, and shared final path during local
  personalization;
- locally update only the allowed personal DoRA parameters in declared middle
  modules;
- reject a checkpoint that fails the compatibility and calibration suite.

The layer counts are hypotheses, not branding. Measure them. If the phone can
honestly support only four blocks or a small DoRA update in the first alpha, report
that instead of forcing six.

## What trains locally

Keep three kinds of learning separate:

### 1. Mutable factual memory

Use a local, encrypted, inspectable memory/retrieval store for facts that must
be corrected, deleted, or attributed. The owner must be able to view, export,
and delete it. This is part of pocket i; it is not evidence that weights learned
the fact.

### 2. Stable personal capability

Use local weight updates for stable skills, procedures, preferences, and
representations that are difficult to reduce to document lookup. The selected
first PEFT method is DoRA: train the declared magnitude and low-rank directional
parameters in personal middle modules while the common base and neural ABI stay
frozen. Full local continual pretraining is not required for the first test.
The detailed gate and UI contract is in `DORA-LANGUAGE-SWARM-PLAN.md`.

### 3. Shared general competence

The pretrained base and shared source path remain frozen during this study.
Shared-model updates require a separate protocol, consent model, and regression
suite.

The trainer must never silently scan a home directory, repository, message
history, or account. Every training item is explicitly selected or generated
from controlled synthetic data. Keep a local held-out set, record the exact
training recipe, compare before/after behavior, and retain a rollback
checkpoint.

## First human-readable task world

Design the dataset before training. It must be readable by a human and must not
collapse into three binary guesses.

Recommended structure:

- three disjoint fictional micro-domains, one per branch;
- each domain contains private symbols and at least one learned transformation,
  not only a fact lookup;
- a test prompt requires one contribution from every domain plus a public
  language operation supplied by `z0`;
- the final output is a short sequence from a large answer space, with exact
  deterministic ground truth;
- central merger training and calibration never see locked private symbols;
- held-out tests use unseen combinations of locally learned elements;
- the complete ground-truth generator is versioned and inspectable.

Before accepting the dataset, calculate and publish the blind-guess probability
for the entire answer. Reject any design in which one branch merely emits a bit
or in which a central model can memorize all test keys.

Include two strata:

1. **Knowledge composition:** establishes that the neural path can carry three
   private learned associations.
2. **Capability composition:** at least one branch contributes a learned
   procedure that an exact document-retrieval baseline does not perform by
   itself.

If only the first stratum works and exact RAG explains the whole gain more
cleanly, say so. Do not invent a neural advantage.

## Work phases

### Phase 0 — explain and obtain approval

Before mutating the environment:

1. Read `METHOD.md`, E001, E002, E003, and this file.
2. Explain the architecture and claim boundary in plain Russian.
3. Inspect `yukabox` hardware, free disk, current Python/toolchain, and
   accelerator availability with read-only commands.
4. Present two or three pinned base-model candidates with expected memory,
   download, training method, license, and risks.
5. Present the proposed human-readable task world and its chance baseline.
6. Wait for explicit human approval.

### Phase 1 — write and freeze the development protocol

After approval:

- create the new experiment directory without rewriting E003;
- add `README.md`, `PROTOCOL.md`, dependency lock, config schema, and an artifact
  manifest format;
- state whether the run is a smoke, development run, locked experiment, or
  replication;
- choose train/calibration/test boundaries before training;
- ensure private local data are absent from central training;
- record model revision, code revision, seeds, quantization, and hardware;
- pre-register metrics and stopping conditions.

Run only a smoke after the development protocol is reviewable. A locked run
requires a second explicit human approval.

### Phase 2 — prove elastic base compatibility

On `yukabox`, without personalization:

- load the pinned teacher/base;
- derive or train the 6-, 12-, and 24-layer base paths;
- verify coherent base behavior;
- measure distillation/interface error for every depth;
- initialize each personal branch from its matching base reference;
- verify fresh delta norms are within a pre-registered tolerance;
- verify all branches produce the same ABI shape and finite bounded outputs;
- record time, RAM/VRAM, disk, and checkpoint hashes.

Do not continue if the shallow branches cannot preserve enough base behavior to
make their deltas interpretable.

### Phase 3 — local personalization on one host

Run three isolated owner directories/processes on `yukabox`:

- each receives only its own controlled training shard;
- each starts from its matching unpersonalized checkpoint;
- only declared personal parameters may receive gradients;
- source, merger, other owners, and locked test labels remain inaccessible;
- every branch records loss, changed parameter names, parameter delta norm,
  held-out local accuracy, and rollback checkpoint;
- training failure or data leakage remains visible in the journal.

The initial experiment uses DoRA for all three depths. Do not call a DoRA update
“full-model training”: it is parameter-efficient fine-tuning. Track magnitude
and direction changes separately and prove that shared weights did not change.

### Phase 4 — compose and ablate

Generate with the source path and run every pre-registered control:

1. shared base only;
2. three fresh, unpersonalized depth-matched branches;
3. each personalized branch alone;
4. every pair of personalized branches;
5. all three personalized branches;
6. all three deltas with `z0` removed;
7. shuffled/wrong branches;
8. one missing branch and explicit abstention;
9. exact relevant-data RAG;
10. text-agent synthesis using the same information;
11. a norm-bounded malformed or adversarial delta;
12. repeated runs under fixed and multiple seeds where stochastic decoding is
    used.

Record exact-match quality, token-level likelihood where useful, per-branch
causal contribution, delta norms, calibration/abstention, bytes, latency,
memory, and total compute. Quality is the first priority, but resource use must
remain visible.

The main hypothesis does not require equal resources: the eventual swarm is
allowed to improve by adding independent data and compute. Equal-budget
controls are diagnostic, not the definition of success.

### Phase 5 — build the microscope before a physical deployment

Create a standalone local HTML artifact that lets a person inspect one task
without reading code. It should show:

- exact public prompt and deterministic ground truth;
- the three controlled local training shards;
- which parameter groups changed and by how much;
- fresh versus trained delta norms;
- a small interpretable projection of each returned capsule;
- the `z0` contribution;
- merge and final token probabilities;
- base, single, pair, full-swarm, no-`z0`, wrong-branch, RAG, and text-agent
  outputs;
- the final claim and every limitation.

Do not publish the artifact automatically. Ask the human to inspect it locally,
then request explicit approval before adding it to `joinmultiplayer.ai`.

### Phase 6 — decide whether physical E004 is justified

Only after the language mechanism passes:

- benchmark the 6-layer/DoRA branch on the actual phone;
- benchmark the 12-layer branch on the Mac;
- keep the 24-layer branch on `yukabox`;
- define signed identity, checkpoint version, allowed memory capsule, and
  explicit owner consent;
- run inference-only compatibility first;
- enable local training only after per-device rollback and deletion work;
- create a fresh private room rather than reusing `N0001`.

The phone may begin as inference plus memory or DoRA training. Do not claim
that a browser trained six full transformer blocks unless the recorded run
actually did so.

## Minimum controls and pass/fail gates

The development protocol must choose numerical thresholds before a locked run.
At minimum, advancement requires:

- fresh personal branches produce deltas near zero;
- local training changes only allowed personal parameters;
- three owners have disjoint training data and central components never receive
  locked answers;
- the full answer space makes blind guessing negligible and reported;
- every required branch has a measurable causal effect on the complete answer;
- the full three-branch path exceeds base, fresh clones, every single branch,
  and every pair on locked tasks;
- removing `z0` causes a pre-specified loss on tasks requiring public language
  competence;
- wrong or shuffled branches do not accidentally solve the test;
- an incomplete payload contributes nothing;
- malformed bounded deltas are detected or safely gated to zero;
- every depth satisfies the frozen ABI contract;
- a clean checkout plus pinned external weights reproduces the result.

The neural route does not have to beat exact RAG in the fact-only stratum. To
justify continued neural work, it must show a measurable advantage in the
capability stratum or another benefit that cannot be explained by having simply
retrieved the hidden facts.

## Stop conditions

Stop and report an inconclusive or negative result instead of repairing the
benchmark after seeing locked results when:

- the source or merger can infer locked private values without personal
  branches;
- a fresh branch has a material non-zero delta;
- shallow and deep branches cannot share a stable ABI;
- local updates destroy base behavior or interface compatibility;
- one branch or one pair solves a supposedly three-way task;
- no-`z0` performs as well on tasks designed to require common language skill;
- exact RAG explains all useful behavior and the neural branch adds no learned
  procedure;
- a result depends on test-set-driven threshold changes;
- the run cannot expose enough evidence for a human to verify what learned.

A failed experiment is an accepted laboratory outcome. Preserve its artifacts
and open the next hypothesis; do not silently overwrite it.

## Security and privacy boundaries

- No personal user data in this phase.
- No silent filesystem, repository, browser-history, account, or message scan.
- No model server exposed publicly.
- No inbound production firewall changes without separate approval.
- No `curl | sh`, unpinned remote code, or secret embedded in a config/artifact.
- Store large weights and private owner state outside Git with restrictive
  permissions.
- Keep public artifacts free of tokens, absolute personal paths, environment
  variables, private prompts, raw hidden activations, and owner memory.
- Treat remote hidden states as untrusted: use finite checks, frozen
  projections, hard norm budgets, contribution caps, anomaly checks, and a
  zero-delta fallback.
- Appending the user's question to a prompt is not a defense against a malicious
  latent vector.

## Journal checkpoints for Morrow

At each checkpoint, the visible response—and therefore the filtered public
journal—should contain:

```text
stage:
hypothesis being tested:
what changed:
what was actually run:
metric or observation:
failure/surprise:
claim boundary:
decision requested from the human:
```

Required human decisions:

1. approve the base-model shortlist and task world;
2. approve the development protocol and first smoke;
3. inspect the microscope;
4. approve the locked protocol;
5. decide whether the result justifies three physical devices;
6. approve any public artifact or model distribution.

## Expected repository deliverables

Do not create all of these before Phase 0 approval. The eventual experiment
should contain:

```text
experiments/EXXX-elastic-personal-delta-lm/
  README.md
  PROTOCOL.md
  MODEL_CARD.md
  DATA_CARD.md
  SECURITY.md
  requirements or lockfile
  configs/
    development.json
    locked.json
  src/
    data.py
    elastic_depth.py
    personal_tower.py
    neural_abi.py
    merger.py
    train_local.py
    evaluate.py
    microscope.py
  tests/
  artifacts/
    README.md
```

Model weights, optimizer states, raw private shards, caches, and secret room
state remain ignored local artifacts. Small summaries, manifests, complete
task-level public-safe records, and the standalone microscope may enter Git
after review.

## Definition of done for this handoff

This handoff is complete when the new plugin-enabled task has:

1. started the filtered public E003 journal as Morrow and repeated its URL;
2. explained the design without claiming a language model already exists;
3. presented the pinned model shortlist and hardware/resource audit;
4. presented a human-readable, non-binary task world and chance calculation;
5. stopped for human approval before downloading or training anything.

The implementation task begins only after that approval.
