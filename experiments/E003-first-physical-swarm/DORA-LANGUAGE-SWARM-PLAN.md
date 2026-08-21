# Plan — trainable language pocket i with DoRA and a public microscope

Status: `DRAFT · requires owner approval before every gate`

This document upgrades the language-model handoff after E003. It describes the
first experiment in which three synthetic language `pocket i` learn different
capabilities, expose compatible neural deltas, and are composed by a source
model. It also defines the public experiment UI that must exist before the
first meaningful training run.

Nothing in this file is an experimental result. The base model, dataset,
thresholds, and physical-device recipe are deliberately not locked yet.

## The question

Can three personal language-model branches learn different private skills with
DoRA, preserve a common neural interface, and solve held-out tasks together
that the base, any single branch, and every pair cannot solve?

This is one small mechanism test for H0001. Passing it would not prove that a
billion-device swarm works, that personal data remain private, or that neural
composition is better than every retrieval system.

## Decisions already made

1. Start from one pinned, pretrained, permissively licensed language-model
   lineage. Do not train language from random weights in this experiment.
2. Build compatible `6`, `12`, and `24` block paths from that lineage.
3. Keep a shared source representation `z0`; personal branches return only
   their bounded contribution above a matching base reference.
4. Use **DoRA**, not LoRA, for the first personal weight updates.
5. Keep mutable facts in inspectable local memory/RAG. DoRA is for stable skills,
   procedures, preferences, and representations.
6. Optimize the first study for quality and inspectability. Bytes, compute, and
   latency are recorded, but are not required to be equal across the swarm and
   a single model.
7. No stage advances automatically. Every gate ends in a visible owner decision.
8. Development failures remain public-safe, labelled, and downloadable. A
   failed run is never silently replaced by a prettier run.

## What “DoRA training” means here

For a selected pretrained linear weight, DoRA writes the weight as a magnitude
and a direction. In simplified notation:

```text
base weight:       W0 = m0 * V0 / ||V0||
personal weight:   Wi = mi * (V0 + Bi Ai) / ||V0 + Bi Ai||
train locally:     mi, Ai, Bi
keep frozen:       W0 and every other owner's DoRA parameters
```

The low-rank matrices change the direction; the learned magnitude can change
the strength. This is the selected PEFT method because it gives the personal
branch more freedom than direction-only LoRA while keeping the number of local
trainable parameters small. It is still fine-tuning, not pretraining from
scratch and not proof that the model learned a new fact reliably.

The first mechanism run uses the same DoRA rank and the same target-module
classes for all three depths so depth is not confused with a different adapter
recipe. A proposed development default is rank `8`, applied to the declared
attention and MLP projections. The exact module list, scaling, dropout, dtype,
optimizer, and rank must be shown at Gate 1 and frozen before a locked run.

Different ranks may later be chosen for real devices, but that is a separate
hardware experiment and must be labelled as such.

### Fresh-branch invariant

A new personal branch must be functionally equal to its matching base path:

```text
PersonalTower_fresh(h) ~= BaseTower_depth(h)
raw_delta_fresh ~= 0
```

DoRA initialization must preserve this equality numerically. The UI must show
the largest and percentile fresh-delta norms before any local learning. If the
pre-registered tolerance is exceeded, training stops.

### The actual neural composition

```text
tokens
  -> shared stem -> h
                    |-> BaseTower_6(h)
                    |-> PersonalTower_phone_6(h, local memory)  -> raw delta 1
                    |-> BaseTower_12(h)
                    |-> PersonalTower_mac_12(h, local memory)   -> raw delta 2
                    |-> BaseTower_24(h)
                    |-> PersonalTower_server_24(h, local memory)-> raw delta 3

delta_i = ClipAndNormalize(Pout_depth(raw_delta_i), norm budget)

next token = FinalLayers(z0 + Merge(delta_1, delta_2, delta_3, metadata))
```

`Pin`, `Pout`, the ABI width, normalization convention, norm budget, source
path, and final path are frozen during personal DoRA training. The experiment
records magnitude changes and directional changes separately, but the merger
receives the bounded canonical delta, never raw owner weights.

## The five kinds of learning

They must never be mixed in reports:

| Part | How it learns | Purpose |
| --- | --- | --- |
| shared pretrained language | reused pinned checkpoint | language and broad competence |
| shallow compatible bases | distillation / compatibility training | make 6/12/24 paths speak one neural ABI |
| personal branch | local DoRA fine-tuning | stable owner-specific skill and behavior |
| local memory | explicit retrieval, not gradient updates | exact, changing, attributable, deletable facts |
| merger/final path | central calibration training on allowed public/surrogate tasks | combine a set of bounded deltas |

Full fine-tuning of personal middle blocks is not part of the first locked run.
It becomes an explicit later ablation if DoRA cannot learn enough. It must use a
new config and cannot overwrite the DoRA result.

## Human-readable task world

Before model training, build three fictional, disjoint micro-domains. Each
owner receives:

- private symbols never shown to the other owners;
- a small stable transformation or procedure, not only a lookup table;
- local train and local held-out examples;
- an explicit set of examples that may enter local RAG;
- an explicit set of examples allowed to update DoRA weights.

Every locked swarm task requires:

1. one learned contribution from all three domains;
2. one public language operation that requires `z0`;
3. a short exact answer drawn from a large known answer space;
4. a human-readable derivation produced by the ground-truth generator.

The merger sees calibration domains and combinations, but never the locked
private keys or their labels. Locked tasks use unseen combinations. Blind-guess
probability is calculated for the complete answer, not for one branch token.

The dataset has two reported strata:

- **knowledge composition:** combine three private associations;
- **capability composition:** combine learned procedures that exact retrieval
  does not execute by itself.

If exact RAG explains all useful behavior, the result says “retrieval won this
task.” That is an accepted outcome.

## Gates: the experiment cannot move without the owner

Every gate has four machine states: `preparing`, `needs_review`, `approved`, and
`rejected`. Only the owner can create `approved` or `rejected`. A process may
prepare evidence, but it may not approve itself or start the next gate.

### Gate 0 — choose the base and the machine budget

Show:

- two or three base-model candidates, exact revisions, parameter counts,
  licenses, tokenizer, and context length;
- yukabox RAM/accelerator/disk benchmark;
- estimated disk, peak memory, and training time for 6/12/24 paths;
- what will be downloaded and from where;
- the exact boundary between reused weights and our new architecture.

Owner decides: model candidate, maximum download, maximum run time, and whether
Gate 1 may begin.

### Gate 1 — approve the task and DoRA recipe

Show:

- 12–20 sample tasks with their full human derivations;
- complete answer space and chance probability;
- train/calibration/locked split by keys and domains;
- exact DoRA target modules, rank, scaling, dropout, optimizer, steps, and
  trainable parameter count for each depth;
- which examples enter weights and which enter local memory;
- proposed numerical pass/fail thresholds.

Owner must be able to edit or reject the task before any learning happens.

### Gate 2 — approve the compatible base family

Train/distill only the base family. Show side by side:

- the same public prompts answered by 6-, 12-, and 24-block paths;
- teacher/student token probabilities and interface error;
- ABI shape, finite-value checks, and latency/memory per depth;
- checkpoint and source-tree hashes;
- fresh personal branches with near-zero raw and projected deltas.

If a shallow path does not preserve enough common competence, stop or revise
the architecture before personal training.

### Gate 3 — approve local DoRA learning

First run only a tiny visible smoke for each synthetic owner. Show:

- exact local shard available to that owner;
- parameters marked trainable and parameters proven unchanged by hash;
- loss curve and local held-out score before/after;
- magnitude change `Δm` and direction update norms separately by module;
- general-anchor regression and ABI compatibility before/after;
- fresh, trained, and rolled-back outputs on the same examples;
- checkpoint size and rollback/delete controls.

No merger training begins until the owner confirms that each branch really
learned its own procedure and did not change shared weights.

### Gate 4 — approve the merger protocol

Show the frozen inputs and pre-register:

- calibration data available to the merger;
- expert dropout, wrong-expert, incomplete, and bounded-malicious simulations;
- all baselines and ablations;
- exact primary metric and all thresholds;
- seeds and stopping rules;
- development versus locked-run labels.

The owner explicitly starts the locked run. Thresholds cannot change afterward.

### Gate 5 — inspect one result under a microscope

Before reading an aggregate headline, inspect at least three individual tasks:

- one success;
- one failure;
- one disagreement or abstention.

For each task the UI displays the public prompt, allowed local evidence,
per-pocket contribution, bounded delta summaries, `z0`, merger influence,
final token probabilities, ground truth, and every control's answer. Raw hidden
states and private records are not published.

Owner decides whether the aggregate evaluation may be opened. This ordering
reduces the temptation to explain individual cases only after seeing a score.

### Gate 6 — accept, reject, or mark inconclusive

Show the complete locked result and artifacts. The only allowed conclusions:

- `mechanism supported within this task world`;
- `mechanism not supported`;
- `inconclusive because ...`.

The owner writes a short decision note. The result and negative evidence remain
visible. Only then may a physical-device protocol be proposed.

### Gate 7 — approve the three real devices

Do inference-only compatibility first. Then separately show and approve:

- phone 6-block DoRA benchmark;
- Mac 12-block DoRA benchmark;
- yukabox 24-block DoRA benchmark;
- per-device local storage, rollback, deletion, thermal, battery, and consent;
- device-specific DoRA rank changes, if any;
- signed checkpoint and ABI versions;
- a new room and a private-to-public artifact boundary.

A phone failure is an experiment result, not permission to call server-side
training “phone training.”

## Required comparisons

The locked matrix includes at least:

1. shared base only;
2. fresh depth-matched branches;
3. each trained pocket i alone;
4. every trained pair;
5. all three trained pocket i;
6. all three with `z0` removed;
7. shuffled and wrong pockets;
8. one incomplete or timed-out pocket, whose partial contribution must be zero;
9. exact relevant-data RAG;
10. text-agent synthesis with the same evidence;
11. DoRA magnitude frozen at its base value;
12. DoRA direction update disabled;
13. a bounded malformed delta;
14. repeated locked seeds.

Conditions 11 and 12 make the DoRA choice inspectable: they test whether the
learned magnitude, learned direction, or both caused the change. They are
diagnostics, not an invitation to pick the nicer number after the run.

## Success and stop rules

Exact numerical thresholds are locked at Gate 1/4. At minimum, progress
requires:

- fresh DoRA branches have near-zero functional deltas;
- only `m`, `A`, and `B` in the declared personal modules change;
- each owner improves on its local held-out procedure;
- general-anchor and ABI regressions stay below the locked limits;
- each required pocket has a measurable causal contribution;
- the full swarm exceeds the base, every single, and every pair on locked tasks;
- removing `z0` loses quality on tasks that require shared language competence;
- wrong, incomplete, non-finite, or over-budget contributions do not help;
- the result reproduces from a clean checkout, pinned weights, config, and seed;
- a human can follow at least one answer end to end in the public microscope.

Stop, preserve, and report when data leak to the merger, chance is misstated,
the base solves locked tasks alone, DoRA damages the common interface, one pair
solves a three-way task, exact RAG explains every gain, or a threshold is edited
after locked results are visible.

## Public UI on joinmultiplayer.ai

The UI is part of the experiment, not a screenshot made after success. Build
the empty experiment page before Gate 1 and let it accumulate an append-only,
public-safe record.

Initial canonical route:

```text
/experiment/?id=E004
```

The existing experiment/journal system should be extended instead of creating
a second incompatible publication mechanism.

### 1. Hypothesis and boundary

Always visible at the top:

- the exact question in Russian and English;
- what this experiment can and cannot prove;
- current phase: design, development, locked, physical, complete, or stopped;
- a loud `DEVELOPMENT — NOT A RESULT` label until Gate 6.

### 2. Human gate timeline

Eight cards show Gate 0–7. Each contains:

- status and timestamp;
- evidence checklist;
- owner decision and public note;
- config/source/artifact hash used for that decision;
- an explicit “waiting for Yuka” state.

Approval controls are private and token-protected. Public visitors see decisions
but cannot approve, restart, or mutate a run.

### 3. Three pocket i cards

One card per synthetic/physical owner:

- device and logical pocket id;
- depth, base revision, DoRA rank, target modules, trainable parameter count;
- local examples count without private contents;
- status: fresh, learning, compatible, rejected, or ready;
- local held-out and general-anchor metrics;
- `Δm`, directional-update norm, final bounded-delta norm;
- checkpoint and ABI hashes;
- a coarse face/constellation that becomes denser only as verified capability
  is added. Decoration must not imply truth or independence.

### 4. Live learning view

Development runs may append rate-limited public-safe metric events:

- step and wall time;
- train and local-held-out loss;
- general-anchor regression;
- magnitude and direction norms;
- ABI error, clipped-delta rate, memory, and device temperature where available.

The chart must show gaps when a device is offline; it must never interpolate a
fake success. Raw prompts, private memory, gradients, hidden states, secrets,
local paths, and owner tokens are never events.

### 5. Task microscope

An interactive task selector shows:

```text
prompt -> z0 -> pocket 1 delta
             -> pocket 2 delta -> merger -> final tokens -> answer
             -> pocket 3 delta
```

The visitor can toggle base, fresh, singles, pairs, full swarm, no-`z0`, RAG,
and text-agent controls. It exposes bounded scalar summaries and interpretable
projections, not raw activations. Every displayed value links to the immutable
task record and run manifest from which it was rendered.

### 6. Result matrix and swarm curve

Show per-stratum exact match, causal loss when each pocket is removed,
calibration, failures, bytes, latency, compute, and all seeds. Also show quality
as independent pockets/data/compute are added. The main claim is allowed to be
about swarm growth; equal-budget values remain visible diagnostic controls, not
the definition of success.

### 7. Artifacts and reproduction

Downloadable public-safe artifacts:

- protocol and frozen config;
- model and data cards;
- source-tree manifest and git revision;
- environment/dependency lock;
- task generator and public task records;
- summary and per-condition metrics;
- checkpoint hashes and a clear statement of whether weights are downloadable;
- microscope HTML/data;
- owner decision log and known limitations.

No artifact is called “open” if its license or privacy boundary prevents
reproduction. Synthetic DoRA weights should be published when the chosen base
license permits it; personal future weights are private by default.

## Minimal API and artifact contract

Reuse experiment runs and append-only journal events. Extend them with a
versioned public manifest rather than placing scientific state in prose only.

```json
{
  "experiment_id": "E004",
  "protocol_version": "draft-v0.1",
  "phase": "development",
  "claim_status": "not_a_result",
  "current_gate": 2,
  "gates": [],
  "pockets": [],
  "runs": [],
  "artifacts": [],
  "updated_at": "..."
}
```

Required event types:

```text
gate_requested
gate_approved
gate_rejected
training_started
metric_recorded
checkpoint_saved
training_stopped
evaluation_finished
artifact_published
run_failed
```

The server validates allowed fields, sizes, monotonic event sequence, experiment
identity, and secret patterns. UI code renders the manifest; it does not infer
an approval or recompute a headline from missing fields.

## Build order

1. Add the E004 protocol skeleton, manifest schema, and owner-gate state machine.
2. Add the empty `/experiment/?id=E004` page with hypothesis, boundary, gates,
   three pocket cards, and artifact list.
3. Add filtered journal events and private approval endpoints; test that a
   process cannot self-approve.
4. Inspect yukabox and choose a pinned base only at Gate 0.
5. Generate the readable task world and DoRA config; render them in Gate 1.
6. Implement and test the elastic base/ABI; publish the Gate 2 microscope.
7. Run three isolated DoRA smokes; publish changed-parameter proofs for Gate 3.
8. Freeze the merger, baselines, thresholds, and locked seeds at Gate 4.
9. Run locked evaluation once; reveal individual microscope cases before the
   aggregate result.
10. Record the Gate 6 human conclusion.
11. Only then write and approve the physical phone/Mac/yukabox protocol.

## First implementation slice

The next coding slice should stop after steps 1–3. It creates the visible,
auditable shell but downloads no model and performs no training. The owner can
then inspect the actual control points on joinmultiplayer.ai before approving
hardware inspection and model selection.

## Method reference

DoRA is based on *DoRA: Weight-Decomposed Low-Rank Adaptation* (Liu et al.,
ICML 2024): <https://arxiv.org/abs/2402.09353>.
