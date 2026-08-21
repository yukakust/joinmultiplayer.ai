# E004 plan — the smallest useful DoRA language-swarm test

Status: `DRAFT · no model downloaded or trained`

## Goal

Run one understandable experiment and publish enough evidence on
`joinmultiplayer.ai` for a person to see what happened.

Question:

> Can three language pocket i learn different small skills in their own DoRA
> weights and solve new tasks together that the base model, any one pocket i,
> and every pair cannot solve?

Passing this experiment supports only this small mechanism. It does not prove a
billion-device swarm, privacy, or superiority over every RAG system.

## What we are building

Use one small pretrained language model for language and create three personal
paths from the same lineage:

```text
shared prompt -> shared representation z0
                     |-> pocket i A -> delta A
                     |-> pocket i B -> delta B
                     |-> pocket i C -> delta C

answer = shared final path(z0 + merge(delta A, delta B, delta C))
```

Each personal path learns with **DoRA**, not LoRA:

```text
base weight:       W0 = m0 * V0 / ||V0||
personal weight:   Wi = mi * (V0 + Bi Ai) / ||V0 + Bi Ai||
train locally:     mi, Ai, Bi
```

The base, neural interface, and other pockets remain frozen. A fresh pocket
must initially behave like its matching base and return a delta near zero.

Mutable facts still belong in local inspectable RAG. This experiment uses DoRA
for a stable rule or procedure, not as a database.

## Only three visible checkpoints

There is no separate approval backend and no eight-stage ceremony. Work stops
three times and the evidence is shown to the owner in Codex and on the public
experiment page.

### Checkpoint 1 — approve the test before training

Show together on one screen:

- the recommended base model and exact revision;
- whether yukabox can run it;
- three example private skills, one per pocket;
- example combined questions and their human-readable solutions;
- complete answer space and blind-guess probability;
- DoRA target modules, rank, trainable parameter count, and expected run time;
- the few numerical criteria below.

The owner can change the task or say “start.” No model training happens before
this decision. A read-only hardware check and model download/checksum are setup,
not separate checkpoints.

### Checkpoint 2 — prove that the three pockets learned

After three isolated DoRA training runs, show for each pocket:

- exactly which synthetic lesson it received;
- before/after answers on local held-out examples;
- held-out score;
- changed parameter groups (`m`, `A`, `B` only);
- magnitude change, direction-update norm, and final bounded-delta norm;
- proof that shared weights and the neural ABI did not change;
- one rollback example.

The owner sees the evidence before merger evaluation starts. If one pocket did
not learn or broke compatibility, stop and report it.

### Checkpoint 3 — inspect and accept the result

Show individual tasks and the complete result table:

- base only;
- each trained pocket alone;
- every pair;
- all three together;
- all three without `z0`;
- wrong or missing pocket;
- exact relevant-data RAG.

The owner can open a successful task and a failed task and trace:

```text
question -> contribution A/B/C -> merge -> token probabilities -> answer
```

Then record one conclusion: supported in this task world, not supported, or
inconclusive.

## The test data

Create three fictional micro-domains. Each pocket receives different symbols
and a small transformation or procedure. A locked question requires all three
procedures plus ordinary language competence from `z0`.

Requirements:

- the answer is not a bit and cannot be guessed with meaningful probability;
- a single pocket or pair lacks information required for the whole answer;
- test questions use unseen combinations;
- the central merger never receives the pockets' locked lessons or answers;
- every task has a deterministic generator and readable derivation;
- one subset tests fact composition and another tests a learned procedure.

If exact RAG explains the entire gain, report that plainly.

## Minimal training sequence

### 1. Choose and prepare the base

- Pick one small, permissively licensed pretrained model.
- Pin revision, tokenizer, license, and checksum.
- Verify ordinary generation on yukabox.
- Produce compatible short, medium, and deep paths from the same lineage. The
  exact depths may be `6/12/24` only if the chosen model and hardware support
  them; otherwise record honest smaller depths.
- Freeze the shared path and the versioned neural ABI.
- Verify that fresh personal deltas are near zero.

This compatibility preparation may use distillation. It is not the personal
experiment result.

### 2. Train three synthetic pocket i with DoRA

- Give each isolated process only its own synthetic lesson.
- Use the same DoRA rank and target-module classes initially so the comparison
  is understandable.
- Update only declared `m`, `A`, and `B` parameters.
- Keep a local held-out set and a rollback checkpoint.
- Record before/after behavior and general-language regression.

### 3. Train the merger

- Freeze the three personal pockets.
- Train the merger only on separate calibration tasks.
- Randomly omit and reorder pockets during calibration.
- Reject incomplete, non-finite, or over-budget deltas.

### 4. Run the locked evaluation once

- Freeze code, config, data split, model hashes, and seeds.
- Run all conditions listed in Checkpoint 3.
- Do not change thresholds after results appear.
- Preserve negative and failed runs.

## Minimal success criteria

Choose exact numbers at Checkpoint 1. At minimum:

- fresh pocket deltas are near zero;
- only DoRA personal parameters change;
- every pocket learns its local held-out procedure without unacceptable common
  language regression;
- all three together beat base, every single pocket, and every pair on locked
  tasks;
- removing any required pocket causes a measurable loss;
- removing `z0` hurts tasks requiring shared language competence;
- invalid or partial deltas contribute nothing;
- the result is reproducible from the pinned config and public-safe artifacts.

## The one required UI

Extend the existing experiment page:

```text
/experiment/?id=E004
```

It needs only five sections:

1. **Question and boundary** — hypothesis, current status, and what the test
   cannot prove.
2. **Three pocket i** — depth, DoRA configuration, fresh/trained state, local
   held-out score, and delta summaries.
3. **Checkpoint** — what is waiting for owner review. The actual approval can
   remain in Codex for the MVP; the site only records the decision.
4. **Microscope** — choose one task and toggle base, singles, pairs, swarm,
   no-`z0`, missing pocket, and RAG.
5. **Result and files** — result table plus protocol, frozen config, summary,
   task records, hashes, limitations, and reproduction command.

The page reads versioned public-safe JSON artifacts. We do not need WebSockets,
live loss charts, a new approval API, device temperature, raw hidden states, or
private training examples for the first test. During training the page may
simply say `running`; after a checkpoint it receives a reviewed snapshot.

## Repository deliverables

```text
experiments/E004-dora-language-swarm/
  README.md
  PROTOCOL.md
  MODEL_CARD.md
  DATA_CARD.md
  config.json
  src/
  tests/
  artifacts/<run-id>/
    checkpoint.json
    summary.json
    tasks.jsonl
    microscope.json
```

The existing filtered Codex journal records progress. Static experiment
artifacts carry the scientific evidence. We do not build a second journal.

## Execution order

1. Build the empty E004 page and artifact schema.
2. Inspect yukabox, recommend one base, and generate sample tasks.
3. Show Checkpoint 1 and wait.
4. Prepare the compatible base paths and train the three DoRA pockets.
5. Publish the reviewed learning snapshot; show Checkpoint 2 and wait.
6. Train the merger and run the locked controls once.
7. Publish the microscope and table; show Checkpoint 3 and record the decision.
8. Only after this result decide whether to move the paths onto phone, Mac, and
   yukabox as a separate physical experiment.

## Explicitly postponed

- training on the three physical devices;
- per-token WAN streaming;
- automatic expert routing;
- user accounts and on-site approval buttons;
- live training telemetry;
- decorative growth/face animations;
- personal human data;
- continuous learning and model updates;
- billion-device scaling and Byzantine security.

These are important later. None is needed to answer the first question.

## Method reference

DoRA follows *DoRA: Weight-Decomposed Low-Rank Adaptation* (Liu et al., ICML
2024): <https://arxiv.org/abs/2402.09353>.
